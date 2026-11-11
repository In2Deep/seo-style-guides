#!/usr/bin/env python3
"""Keep local copies of Google developer guides (style, SEO, crawling) and check them for changes.

Google offers its docs over MCP only with Gemini, which this project doesn't use, so these copies
stand in. Google serves each page on developers.google.com as Markdown at the page's address plus
".md.txt". For each guide, this script reads the guide's navigation, downloads every page's
Markdown (plus any page of the guide those pages link to that the navigation leaves out), and
compares each page's SHA-256 with the SHA256SUMS file in the guide's folder.

Guides, each in its own folder under guides/:
    style  Google developer documentation style guide  https://developers.google.com/style
    seo    Google Search Central SEO documentation      https://developers.google.com/search/docs
    crawling  Google crawling infrastructure documentation  https://developers.google.com/crawling

Pages are saved byte for byte as Google serves them, so the standard tool also verifies a copy:
    cd guides/seo && shasum -a 256 -c SHA256SUMS

Run (Python 3.10+, standard library only):
    python3 sync_google_docs.py                     # check every guide; write nothing
    python3 sync_google_docs.py --guide seo         # check one guide
    python3 sync_google_docs.py --guide seo --save  # update its pages, SHA256SUMS and README.md
After --save, `git diff guides` shows exactly what Google changed.

Exit status: 0 every copy checked is current (or --save updated it), 1 a copy is out of date,
2 a guide could not be fetched.

Other tools import this module: check_guide() returns what a check found without printing or
writing, save_check() saves it, and read_saved_pages() lists a local copy's pages from its README.
The MCP server in mcp-server/ serves the copies this way.
"""
import argparse
import hashlib
import html
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parent
SNAPSHOT_ROOT = REPO_ROOT / "guides"
SCRIPT_PATH = Path(__file__).resolve().relative_to(REPO_ROOT)

SITE_HOST = "developers.google.com"
SITE_ORIGIN = f"https://{SITE_HOST}"
MARKDOWN_SUFFIX = ".md.txt"
MARKDOWN_CONTENT_TYPE = "text/markdown"
REQUEST_HEADERS = {"User-Agent": "seo-style-guides-sync/1.0 (python-urllib)", "Accept-Language": "en"}
REQUEST_DELAY_SECONDS = 0.25
REQUEST_TIMEOUT_SECONDS = 30
RETRY_ATTEMPTS = 3
RETRYABLE_HTTP_CODES = {429, 500, 502, 503, 504}

FIRST_SECTION = "Introduction"
SECTION_JOINER = " › "
UNLISTED_SECTION = "Linked from the guide but not in its navigation"
PATH_SEPARATOR_IN_FILE_NAME = "--"
PAGE_FILE_NAME = re.compile(r"^[a-z0-9_-]+\.md$")
MARKDOWN_LINK_TARGET = re.compile(r"\]\(<?([^)\s>]+)")
HTML_TITLE = re.compile(r"<title>\s*([^<|]+)")
SNAPSHOT_DATE_LINE = re.compile(r"^- Snapshot: (\d{4}-\d{2}-\d{2})", re.M)
PAGES_HEADING = "## Pages"
SECTION_HEADING_PREFIX = "### "
README_PAGE_LINE = re.compile(r"^- \[(.*)\]\(([^)\s]+)\): <([^>\s]+)>$")


@dataclass(frozen=True)
class Guide:
    key: str  # command-line name and folder name, such as "seo"
    title: str
    root_path: str  # site path every page of the guide starts with, such as "/search/docs"
    change_notes: str  # Markdown link to Google's own list of changes
    home_path: str = ""  # the guide's landing page, when it isn't root_path
    navigation_path: str = ""  # a page that shows the guide's menu, when root_path doesn't

    @property
    def folder(self) -> Path:
        return SNAPSHOT_ROOT / self.key

    @property
    def checksum_file(self) -> Path:
        return self.folder / "SHA256SUMS"

    @property
    def readme_file(self) -> Path:
        return self.folder / "README.md"

    @property
    def home_url(self) -> str:
        return SITE_ORIGIN + (self.home_path or self.root_path)

    @property
    def navigation_url(self) -> str:
        return SITE_ORIGIN + (self.navigation_path or self.root_path)

    def path_of(self, href: str) -> str | None:
        """Return the site path for a link to a page of this guide, or None for any other link."""
        parts = urlsplit(href)
        if parts.netloc not in ("", SITE_HOST):
            return None
        path = parts.path.removesuffix(MARKDOWN_SUFFIX).rstrip("/")
        if path != self.root_path and not path.startswith(self.root_path + "/"):
            return None
        if "." in path.rsplit("/", 1)[-1]:
            return None  # an image or other file, not a page
        return path

    def file_name(self, path: str) -> str:
        relative = path[len(self.root_path):].strip("/")
        return f"{relative.replace('/', PATH_SEPARATOR_IN_FILE_NAME) or 'index'}.md"


GUIDES = {
    guide.key: guide
    for guide in (
        Guide("style", "Google developer documentation style guide", "/style", "[What's new](whats-new.md)"),
        Guide(
            "seo",
            "Google Search Central SEO documentation",
            "/search/docs",
            "[Search Central documentation updates](https://developers.google.com/search/updates)",
        ),
        Guide(
            "crawling",
            "Google crawling infrastructure documentation",
            "/crawling/docs",
            "[Changelog](changelog.md)",
            home_path="/crawling",  # /crawling/docs itself is a 404
            navigation_path="/crawling/docs/crawlers-fetchers/overview-google-crawlers",
        ),
    )
}


class FetchError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class GuidePage:
    path: str  # site path, such as "/style/word-list"
    title: str
    section: str

    @property
    def page_url(self) -> str:
        return SITE_ORIGIN + self.path

    @property
    def markdown_url(self) -> str:
        return self.page_url + MARKDOWN_SUFFIX

    @property
    def is_unlisted(self) -> bool:
        return self.section == UNLISTED_SECTION


@dataclass(frozen=True)
class Unavailable:
    """A guide page that could not be saved, and why."""

    kind: str  # "no-md", "dead" or "moved"
    url: str
    reason: str


UNAVAILABLE_ORDER = {"no-md": 0, "dead": 1, "moved": 2}


@dataclass
class Comparison:
    changed: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    edited_locally: list[str] = field(default_factory=list)
    navigation_changed: bool = False
    readme_out_of_date: bool = False

    @property
    def upstream_changed(self) -> bool:
        return bool(self.changed or self.added or self.removed or self.navigation_changed)

    @property
    def copy_out_of_date(self) -> bool:
        return self.upstream_changed or bool(self.edited_locally) or self.readme_out_of_date


@dataclass
class GuideCheck:
    """What checking one guide found: Google's current pages, compared with the local copy."""

    guide: Guide
    pages: list[GuidePage]  # in guide order
    contents: dict[str, bytes]  # each page's Markdown, keyed by file name
    unavailable: list[Unavailable]
    comparison: Comparison
    has_local_copy: bool

    @property
    def is_current(self) -> bool:
        return self.has_local_copy and not self.comparison.copy_out_of_date

    @property
    def titles_by_file_name(self) -> dict[str, str]:
        return {self.guide.file_name(page.path): page.title for page in self.pages}


ProgressCallback = Callable[[Guide, int, int], None]  # (guide, pages fetched, pages known so far)


class NavigationParser(HTMLParser):
    """Collect (section, title, href) for each link in a guide's left-hand navigation menu.

    A section is the menu heading plus any collapsible groups the link sits in, such as
    "Crawling and indexing › Robots.txt".
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[tuple[str, str, str]] = []
        self._menu_depth = 0  # <ul> nesting inside the navigation menu; 0 means outside it
        self._menu_seen = False
        self._heading = ""
        self._groups: list[tuple[int, str]] = []  # (menu depth of the group's <ul>, group label)
        self._in_heading_item = False
        self._in_label = False
        self._link_href: str | None = None
        self._label_for_next_list: str | None = None
        self._text: list[str] = []

    @property
    def _section(self) -> str:
        labels = [self._heading] + [label for _, label in self._groups]
        return SECTION_JOINER.join(label for label in labels if label) or FIRST_SECTION

    def _collected_text(self) -> str:
        return " ".join("".join(self._text).split())

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = (attributes.get("class") or "").split()
        if tag == "ul":
            if self._menu_depth:
                self._menu_depth += 1
                if self._label_for_next_list:
                    self._groups.append((self._menu_depth, self._label_for_next_list))
                    self._label_for_next_list = None
            elif attributes.get("menu") == "_book" and not self._menu_seen:
                self._menu_depth, self._menu_seen = 1, True
        elif not self._menu_depth:
            return
        elif tag == "li":
            self._in_heading_item = "devsite-nav-heading" in classes
            self._label_for_next_list = None
        elif tag == "div" and "devsite-nav-title-no-path" in classes:
            self._in_label, self._text = True, []
        elif tag == "a" and "devsite-nav-title" in classes:
            self._link_href, self._text = attributes.get("href") or "", []

    def handle_data(self, data):
        if self._in_label or self._link_href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if not self._menu_depth:
            return
        if tag == "ul":
            if self._groups and self._groups[-1][0] == self._menu_depth:
                self._groups.pop()
            self._menu_depth -= 1
        elif tag == "div" and self._in_label:
            self._in_label = False
            if self._in_heading_item:
                self._heading, self._groups = self._collected_text(), []
            else:
                self._label_for_next_list = self._collected_text()
        elif tag == "a" and self._link_href is not None:
            title = self._collected_text()
            self.entries.append((self._section, title, self._link_href))
            self._link_href = None
            self._label_for_next_list = title  # a page link can also head a collapsible group


def fetch(url: str, method: str = "GET") -> tuple[str, bytes, str]:
    """Return the content type, body and final URL, retrying rate limits and server errors."""
    request = urllib.request.Request(url, headers=REQUEST_HEADERS, method=method)
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                return response.headers.get_content_type(), response.read(), response.geturl()
        except urllib.error.HTTPError as error:
            if error.code not in RETRYABLE_HTTP_CODES or attempt == RETRY_ATTEMPTS:
                raise FetchError(f"HTTP {error.code} for {url}", error.code) from error
        except (urllib.error.URLError, TimeoutError) as error:
            if attempt == RETRY_ATTEMPTS:
                raise FetchError(f"{error} for {url}") from error
        time.sleep(2 * attempt)
    raise AssertionError("unreachable")


def is_client_error(error: FetchError) -> bool:
    return error.status is not None and 400 <= error.status < 500


def read_navigation(guide: Guide) -> list[GuidePage]:
    """Return the guide's pages in navigation order, with their titles and sections."""
    _, body, _ = fetch(guide.navigation_url)
    parser = NavigationParser()
    parser.feed(body.decode("utf-8"))
    pages: dict[str, GuidePage] = {}
    for section, title, href in parser.entries:
        path = guide.path_of(href)
        if path and path not in pages:
            pages[path] = GuidePage(path, title, section)
    if not pages:
        raise FetchError(f"found no pages in the navigation of {guide.navigation_url}; Google may have changed its layout")
    return list(pages.values())


def read_page_title(page_url: str) -> str:
    """Return a page's title from its HTML, falling back to one made from its address."""
    try:
        _, body, _ = fetch(page_url)
        match = HTML_TITLE.search(body.decode("utf-8", errors="replace"))
    except FetchError:
        match = None
    if match:
        return html.unescape(match.group(1)).strip()
    return page_url.rsplit("/", 1)[-1].replace("-", " ").capitalize()


def fetch_markdown(guide: Guide, page: GuidePage) -> tuple[bytes | None, str | None, Unavailable | None]:
    """Return a page's Markdown, the guide path that serves it, and why nothing was saved.

    A page found only through a link counts only if its web address still serves it, because
    Google keeps serving Markdown for some retired pages. An old address that redirects within
    the guide returns (None, the path it redirects to, None).
    """
    if page.is_unlisted:
        try:
            _, _, final_url = fetch(page.page_url, method="HEAD")
        except FetchError as error:
            if is_client_error(error):
                return None, None, Unavailable("dead", page.page_url, "linked from the guide, but nothing is there")
            raise
        live_path = guide.path_of(final_url)
        if live_path is None:
            return None, None, Unavailable("moved", page.page_url, f"now outside this guide, at {final_url}")
        if live_path != page.path:
            return None, live_path, None
    no_markdown = Unavailable("no-md", page.page_url, "has no Markdown version, so it isn't saved")
    try:
        content_type, body, final_url = fetch(page.markdown_url)
    except FetchError as error:
        if is_client_error(error):
            return None, None, no_markdown
        raise
    if content_type != MARKDOWN_CONTENT_TYPE:
        return None, None, no_markdown
    return body, guide.path_of(final_url), None


def report_progress(guide: Guide, done: int, total: int) -> None:
    if sys.stderr.isatty():
        end = "\n" if done == total else ""
        print(f"\r{guide.key}: fetching pages {done}/{total}", end=end, file=sys.stderr, flush=True)


def download_guide(
    guide: Guide, on_progress: ProgressCallback = report_progress
) -> tuple[list[GuidePage], dict[str, bytes], list[Unavailable]]:
    """Fetch every navigation page of the guide, then any unlisted guide page they link to.

    Old addresses that redirect to another page are followed, not saved twice.
    Returns the pages in guide order, their Markdown keyed by file name, and the pages that
    could not be saved.
    """
    pages = {page.path: page for page in read_navigation(guide)}
    queue = list(pages)
    queued_paths = set(queue)  # every path ever queued, so a page that dropped out isn't queued again
    contents: dict[str, bytes] = {}
    unavailable: list[Unavailable] = []

    def add_unlisted_page(path: str) -> None:
        if path not in queued_paths:
            queued_paths.add(path)
            pages[path] = GuidePage(path, "", UNLISTED_SECTION)
            queue.append(path)

    while queue:
        page = pages[queue.pop(0)]
        body, served_path, reason = fetch_markdown(guide, page)
        time.sleep(REQUEST_DELAY_SECONDS)
        if served_path != page.path:
            del pages[page.path]
            if served_path is not None:
                add_unlisted_page(served_path)
            if reason:
                unavailable.append(reason)
            continue
        file_name = guide.file_name(page.path)
        if file_name in contents:
            raise FetchError(f"two pages map to the file name {file_name}, one of them {page.page_url}")
        if page.is_unlisted:
            pages[page.path] = GuidePage(page.path, read_page_title(page.page_url), page.section)
        contents[file_name] = body
        for target in MARKDOWN_LINK_TARGET.findall(body.decode("utf-8", errors="replace")):
            linked_path = guide.path_of(target)
            if linked_path:
                add_unlisted_page(linked_path)
        on_progress(guide, len(contents), len(contents) + len(queue))
    unavailable.sort(key=lambda item: UNAVAILABLE_ORDER[item.kind])
    return list(pages.values()), contents, unavailable


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_saved_checksums(guide: Guide) -> dict[str, str]:
    """Return {file name: SHA-256} from the guide's SHA256SUMS (the `shasum -a 256` format)."""
    if not guide.checksum_file.exists():
        return {}
    checksums = {}
    for line in guide.checksum_file.read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        name = name.lstrip("*")
        if not PAGE_FILE_NAME.match(name):
            raise ValueError(f"unexpected file name in {guide.checksum_file}: {name!r}")
        checksums[name] = digest
    return checksums


def saved_snapshot_date(guide: Guide) -> str | None:
    if not guide.readme_file.exists():
        return None
    match = SNAPSHOT_DATE_LINE.search(guide.readme_file.read_text())
    return match.group(1) if match else None


def render_readme(guide: Guide, pages: list[GuidePage], snapshot_date: str) -> str:
    folder = guide.folder.relative_to(REPO_ROOT)
    lines = [
        f"# {guide.title} (local copy)",
        "",
        f"A copy of <{guide.home_url}> for writers and AI agents working in this repo.",
        "Google offers its docs over MCP only with Gemini, which this project doesn't use, so this copy stands in.",
        f"Generated by `{SCRIPT_PATH}`; don't edit anything in this folder by hand.",
        "",
        f"- Snapshot: {snapshot_date}, {len(pages)} pages.",
        f"- Source: each page's Markdown, served at the page's address plus `{MARKDOWN_SUFFIX}`, saved byte for byte.",
        f"- File names: the page's address after `{guide.root_path}/`, with `{PATH_SEPARATOR_IN_FILE_NAME}` for each `/`.",
        "- Checksums: `SHA256SUMS` holds each page's SHA-256.",
        f"- License: Google LLC, \"{guide.title}\". Page content is under",
        "  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) and code samples under",
        "  [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0); see the",
        "  [Google Developers Site Policies](https://developers.google.com/site-policies).",
        f"- Google's own change notes: {guide.change_notes}.",
        "",
        "## Check for changes or update",
        "",
        "```bash",
        f"python3 {SCRIPT_PATH} --guide {guide.key}          # check only; exit status 1 means the copy is out of date",
        f"python3 {SCRIPT_PATH} --guide {guide.key} --save   # update, then: git diff {folder}",
        f"cd {folder} && shasum -a 256 -c SHA256SUMS   # verify the local files",
        "```",
        "",
        PAGES_HEADING,
    ]
    current_section = None
    for page in pages:
        if page.section != current_section:
            current_section = page.section
            lines += ["", f"### {current_section}", ""]
        lines.append(f"- [{page.title}]({guide.file_name(page.path)}): <{page.page_url}>")
    return "\n".join(lines) + "\n"


def page_listing(readme_text: str) -> str:
    return readme_text.partition(PAGES_HEADING)[2]


def read_saved_pages(guide: Guide) -> list[GuidePage]:
    """Return the pages the local copy's README.md lists, in guide order; it reverses render_readme."""
    if not guide.readme_file.exists():
        return []
    pages = []
    section = FIRST_SECTION
    for line in page_listing(guide.readme_file.read_text()).splitlines():
        if line.startswith(SECTION_HEADING_PREFIX):
            section = line.removeprefix(SECTION_HEADING_PREFIX)
        elif match := README_PAGE_LINE.match(line):
            title, file_name, page_url = match.groups()
            path = guide.path_of(page_url)
            if path is None or guide.file_name(path) != file_name:
                raise ValueError(f"unexpected page line in {guide.readme_file}: {line!r}")
            pages.append(GuidePage(path, title, section))
    return pages


def compare(guide: Guide, fetched: dict[str, str], saved: dict[str, str], readme_now: str) -> Comparison:
    comparison = Comparison()
    comparison.changed = sorted(name for name in fetched.keys() & saved.keys() if fetched[name] != saved[name])
    comparison.added = sorted(fetched.keys() - saved.keys())
    comparison.removed = sorted(saved.keys() - fetched.keys())
    for name, digest in sorted(saved.items()):
        local_file = guide.folder / name
        if not local_file.exists() or sha256_hex(local_file.read_bytes()) != digest:
            comparison.edited_locally.append(name)
    if saved:
        readme_saved = guide.readme_file.read_text() if guide.readme_file.exists() else ""
        comparison.navigation_changed = page_listing(readme_saved) != page_listing(readme_now)
        comparison.readme_out_of_date = readme_saved != readme_now
    return comparison


def save_snapshot(guide: Guide, contents: dict[str, bytes], removed: list[str], readme_text: str) -> None:
    guide.folder.mkdir(parents=True, exist_ok=True)
    for name, body in contents.items():
        target = guide.folder / name
        if not target.exists() or target.read_bytes() != body:
            target.write_bytes(body)
    for name in removed:
        (guide.folder / name).unlink(missing_ok=True)
    checksum_lines = (f"{sha256_hex(contents[name])}  {name}\n" for name in sorted(contents))
    guide.checksum_file.write_text("".join(checksum_lines))
    guide.readme_file.write_text(readme_text)


def check_guide(guide: Guide, on_progress: ProgressCallback = report_progress) -> GuideCheck:
    """Fetch the guide from Google and compare it with the local copy, writing nothing.

    Raises FetchError when the guide can't be fetched.
    """
    pages, contents, unavailable = download_guide(guide, on_progress)
    saved_checksums = read_saved_checksums(guide)
    fetched_checksums = {name: sha256_hex(body) for name, body in contents.items()}
    readme_with_saved_date = render_readme(guide, pages, saved_snapshot_date(guide) or date.today().isoformat())
    comparison = compare(guide, fetched_checksums, saved_checksums, readme_with_saved_date)
    return GuideCheck(guide, pages, contents, unavailable, comparison, has_local_copy=bool(saved_checksums))


def save_check(check: GuideCheck) -> None:
    """Make the local copy match what the check fetched, dated today."""
    readme_text = render_readme(check.guide, check.pages, date.today().isoformat())
    save_snapshot(check.guide, check.contents, check.comparison.removed, readme_text)


def print_report(check: GuideCheck) -> None:
    guide, comparison, titles = check.guide, check.comparison, check.titles_by_file_name
    print(f"{guide.title}: {len(check.pages)} pages fetched and compared with {guide.checksum_file.relative_to(REPO_ROOT)}.")
    for label, names in (("changed", comparison.changed), ("new", comparison.added), ("removed", comparison.removed)):
        for name in names:
            print(f"  {label:<8} {name:<44} {titles.get(name, '')}".rstrip())
    if comparison.navigation_changed:
        print("  nav      page titles, sections or order changed (README.md page list)")
    elif comparison.readme_out_of_date:
        print("  readme   README.md was written by an older version of this script")
    for name in comparison.edited_locally:
        print(f"  local    {name} differs from SHA256SUMS (edited or deleted here)")
    for item in check.unavailable:
        print(f"  {item.kind:<8} {item.url} ({item.reason})")


def sync_guide(guide: Guide, save: bool) -> int:
    """Check one guide's local copy, and update it when `save` is set. Returns the exit status."""
    try:
        check = check_guide(guide)
    except FetchError as error:
        print(f"{guide.title}: could not fetch the guide: {error}", file=sys.stderr)
        return 2
    print_report(check)

    if check.is_current:
        print("No changes: the local copy matches Google's current guide.")
        return 0
    if not check.has_local_copy:
        print("No local copy yet.")
    elif check.comparison.upstream_changed:
        print(f"Google changed the guide. Their notes: {guide.change_notes}")

    if not save:
        print(f"Run with --guide {guide.key} --save to update the local copy.")
        return 1
    save_check(check)
    print(f"Saved {len(check.contents)} pages. Review with: git diff {guide.folder.relative_to(REPO_ROOT)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--guide", choices=[*GUIDES, "all"], default="all", help="which guide to check (default: all)")
    parser.add_argument("--save", action="store_true", help="update the local copy instead of only checking it")
    args = parser.parse_args()

    selected = GUIDES.values() if args.guide == "all" else [GUIDES[args.guide]]
    statuses = []
    for index, guide in enumerate(selected):
        if index:
            print()
        statuses.append(sync_guide(guide, args.save))
    return max(statuses)


if __name__ == "__main__":
    sys.exit(main())
