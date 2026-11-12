#!/usr/bin/env python3
"""MCP server (stdio) for the local copies of Google's developer guides in guides/.

Google offers its docs over MCP only with Gemini, which this project doesn't use. This server
serves the verbatim copies that sync_google_docs.py keeps (the developer documentation style
guide, the Search Central SEO docs and the crawling infrastructure docs) and runs that script's
check and update, so agents can use the guides without reading whole folders.

Tools:
    search_google_docs  find a phrase in the saved pages: file:line hits with each page's source URL, then the closest sections by meaning
    read_google_doc     one saved page, or one section or line range of it
    check_google_quote  whether a quote appears verbatim in one saved page
    list_google_docs    a guide's pages by section, from its README.md
    check_google_docs   compare the copies with Google's live guides (writes nothing)
    update_google_docs  save Google's current version of one guide (the script's --save)
    google_docs_job     progress and result of a check or update

A check fetches every page one at a time (about 4 minutes for all three guides), longer than a
client may wait for one tool call, so checks and updates run as background jobs. Each call waits
up to wait_seconds for its job and otherwise returns the job id to ask google_docs_job about.
Jobs last as long as this process.

Protocol: MCP over stdio (newline-delimited JSON-RPC 2.0) with the initialize handshake, revisions
2024-11-05 to 2025-11-25. A client that first probes with server/discover gets "method not found"
and falls back to initialize. Standard library only (Python 3.10+), so there is nothing to install.

Run: started by the MCP client through launch.sh (registered as google_seo_and_style_guides in .mcp.json).
Test: python3 -B -m unittest discover -s mcp-server
"""
import json
import os
import difflib
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from itertools import count
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sync_google_docs as sync  # noqa: E402  (the repo root is on the path only from the line above)
import vectors  # noqa: E402
from vectors import headings  # noqa: E402

SERVER_NAME = "google_seo_and_style_guides"
SERVER_VERSION = "1.0.0"
HANDSHAKE_PROTOCOL_VERSIONS = ("2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25")
LATEST_PROTOCOL_VERSION = HANDSHAKE_PROTOCOL_VERSIONS[-1]
SERVER_INSTRUCTIONS = (
    "Verbatim local copies of three Google guides in guides/: the developer "
    "documentation style guide (style), the Search Central SEO docs (seo) and the crawling "
    "infrastructure docs (crawling: robots.txt, Googlebot, crawl budget). Find pages with "
    "search_google_docs or list_google_docs, read them with read_google_doc, and cite each page's "
    "source URL. search_google_docs also lists the sections closest in meaning, so a question in plain words "
    "works; check_google_quote confirms a quote appears verbatim in a page. The copies are a snapshot: check_google_docs compares them with Google's live "
    "guides; update_google_docs overwrites a copy, so run it only when the user asks."
)

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
REQUEST_WORKERS = 8  # tool calls run in parallel, so a call waiting on a job never blocks a search

ALL_GUIDES = "all"
GUIDE_KEYS = list(sync.GUIDES)
SEARCH_RESULTS_DEFAULT = 30
SEARCH_RESULTS_MAX = 200
MEANING_RESULTS = 5
LINES_SHOWN_PER_PAGE = 3
OTHER_PAGES_LISTED = 20
SNIPPET_LENGTH = 240
READ_LINES_DEFAULT = 400
READ_LINES_MAX = 2000
JOB_WAIT_DEFAULT_SECONDS = 50  # under the 60-second tool timeout some clients use
JOB_WAIT_MAX_SECONDS = 240

class ToolError(Exception):
    """A problem with a tool call's arguments or the files it asks for, reported to the caller as a tool error."""


class RpcError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def selected_guides(guide: str) -> list[sync.Guide]:
    if guide == ALL_GUIDES:
        return list(sync.GUIDES.values())
    if guide in sync.GUIDES:
        return [sync.GUIDES[guide]]
    raise ToolError(f"unknown guide {guide!r}; use one of {', '.join(GUIDE_KEYS)} or {ALL_GUIDES}")


def repo_path(guide: sync.Guide, file_name: str) -> str:
    return str((guide.folder / file_name).relative_to(sync.REPO_ROOT))


def saved_pages_by_file_name(guide: sync.Guide) -> dict[str, sync.GuidePage]:
    """The local copy's pages in guide order, keyed by file name."""
    return {guide.file_name(page.path): page for page in sync.read_saved_pages(guide)}


# --- search_google_docs ---------------------------------------------------------------------


@dataclass
class PageHits:
    guide: sync.Guide
    file_name: str
    page: sync.GuidePage
    lines: list[tuple[int, str]]  # (line number, line) for each matching line
    title_matches: bool


def find_page_hits(guides: list[sync.Guide], line_matches: Callable[[str], bool]) -> list[PageHits]:
    found = []
    for guide in guides:
        for file_name, page in saved_pages_by_file_name(guide).items():
            text = (guide.folder / file_name).read_text(encoding="utf-8", errors="replace")
            lines = [(number, line) for number, line in enumerate(text.splitlines(), 1) if line_matches(line.casefold())]
            if lines:
                found.append(PageHits(guide, file_name, page, lines, line_matches(page.title.casefold())))
    return found


def snippet(line: str, first_word: str) -> str:
    """The line without surrounding space, cut to SNIPPET_LENGTH around the first match."""
    line = line.strip()
    if len(line) <= SNIPPET_LENGTH:
        return line
    start = max(0, line.casefold().find(first_word) - SNIPPET_LENGTH // 3)
    end = start + SNIPPET_LENGTH
    return ("…" if start else "") + line[start:end] + ("…" if end < len(line) else "")


def search_google_docs(query: str, guide: str = ALL_GUIDES, max_results: int = SEARCH_RESULTS_DEFAULT) -> str:
    phrase = " ".join(query.split()).casefold()
    if not phrase:
        raise ToolError("query is empty")
    guides = selected_guides(guide)
    max_results = min(max(max_results, 1), SEARCH_RESULTS_MAX)

    match_mode = "phrase"
    hits = find_page_hits(guides, lambda folded_line: phrase in folded_line)
    words = phrase.split()
    if not hits and len(words) > 1:
        match_mode = "every word on one line"
        hits = find_page_hits(guides, lambda folded_line: all(word in folded_line for word in words))
    scope = "all guides" if guide == ALL_GUIDES else f"guide {guide}"
    if not hits:
        return f'No saved page in {scope} contains "{query}" (case-insensitive phrase, then every word on one line).\n\n' + by_meaning(query, guides)

    hits.sort(key=lambda page_hits: (not page_hits.title_matches, -len(page_hits.lines)))  # stable: guide order breaks ties
    total_lines = sum(len(page_hits.lines) for page_hits in hits)
    shown_pages: list[str] = []
    shown_lines = 0
    for page_hits in hits:
        if shown_lines >= max_results:
            break
        lines = page_hits.lines[: min(LINES_SHOWN_PER_PAGE, max_results - shown_lines)]
        shown_lines += len(lines)
        block = [
            f"{repo_path(page_hits.guide, page_hits.file_name)}: {page_hits.page.title}",
            f"  source: {page_hits.page.page_url}",
            *(f"  {number}: {snippet(line, words[0])}" for number, line in lines),
        ]
        if len(page_hits.lines) > len(lines):
            block.append(f"  (+{len(page_hits.lines) - len(lines)} more matching lines in this page)")
        shown_pages.append("\n".join(block))

    summary = (
        f'"{query}" ({match_mode}, case-insensitive): {total_lines} matching lines in {len(hits)} pages of {scope}. '
        f"Pages whose title matches come first, then pages with the most matches."
    )
    other_pages = hits[len(shown_pages):]
    parts = [summary, *shown_pages]
    if other_pages:
        listed = [
            f"- {repo_path(page_hits.guide, page_hits.file_name)} ({len(page_hits.lines)}): {page_hits.page.title}"
            for page_hits in other_pages[:OTHER_PAGES_LISTED]
        ]
        more = len(other_pages) - len(listed)
        parts.append("Other pages with matches (matching lines):\n" + "\n".join(listed) + (f"\n- and {more} more" if more > 0 else ""))
    parts.append(by_meaning(query, guides))
    return "\n\n".join(parts)


def by_meaning(query: str, guides: list[sync.Guide]) -> str:
    """The sections closest in meaning to the query, or one line saying why that search is off."""
    try:
        closest = vectors.search(query, {selected.key for selected in guides}, MEANING_RESULTS)
    except RuntimeError as error:
        return f"Search by meaning is off: {error}."
    lines = ["Closest sections by meaning (read one with read_google_doc page + section or start_line):"]
    for score, piece in closest:
        path = repo_path(sync.GUIDES[piece["guide"]], piece["file"])
        lines.append(f'- {path}: {piece["title"]} › {piece["heading"]} (lines {piece["first_line"]}–{piece["last_line"]}, score {score:.2f})')
        lines.append(f'  source: {piece["url"]}')
    return "\n".join(lines)


# --- read_google_doc ------------------------------------------------------------------------


def find_saved_page(page: str, guide: str) -> tuple[sync.Guide, str]:
    """Resolve a page given as a file name, repo path, site path or URL to (guide, file name)."""
    reference = page.strip()
    if not reference:
        raise ToolError("page is empty")
    candidates = selected_guides(guide) if guide else list(sync.GUIDES.values())

    for candidate in candidates:  # a developers.google.com address or a site path such as /style/word-list
        path = candidate.path_of(reference.removesuffix(".md"))
        if path:
            return candidate, require_saved_file(candidate, candidate.file_name(path))

    if "://" in reference:
        homes = ", ".join(candidate.home_url for candidate in candidates)
        raise ToolError(f"{reference} is not a page of a saved guide ({homes})")

    parts = reference.strip("/").split("/")
    if len(parts) > 1 and parts[-2] in sync.GUIDES:  # a repo path, or guide/file name
        named_guide = sync.GUIDES[parts[-2]]
        if guide and named_guide.key != guide:
            raise ToolError(f"{reference} is in guide {named_guide.key}, not {guide}")
        return named_guide, require_saved_file(named_guide, parts[-1])

    file_name = reference.replace("/", sync.PATH_SEPARATOR_IN_FILE_NAME)  # a path within the guide
    file_name = file_name if file_name.endswith(".md") else f"{file_name}.md"
    holders = [candidate for candidate in candidates if (candidate.folder / file_name).is_file()]
    if len(holders) > 1:
        raise ToolError(f"{file_name} is in several guides ({', '.join(holder.key for holder in holders)}); name the guide")
    if not holders:
        raise ToolError(f"no saved page {file_name}; find pages with search_google_docs or list_google_docs")
    return holders[0], require_saved_file(holders[0], file_name)


def require_saved_file(guide: sync.Guide, file_name: str) -> str:
    file_name = file_name if file_name.endswith(".md") else f"{file_name}.md"
    if not sync.PAGE_FILE_NAME.match(file_name) or not (guide.folder / file_name).is_file():
        raise ToolError(f"no saved page {file_name} in guide {guide.key}; find pages with search_google_docs or list_google_docs")
    return file_name


def section_range(lines: list[str], section: str) -> tuple[int, int, str]:
    """(first index, end index, heading) of the section whose heading best matches `section`."""
    wanted = " ".join(section.split()).casefold().strip("#` ")
    all_headings = headings(lines)
    exact = [heading for heading in all_headings if heading[2].casefold().strip("` ") == wanted]
    partial = [heading for heading in all_headings if wanted in heading[2].casefold()]
    matches = exact or partial
    if not matches:
        listed = "\n".join(f"{'#' * level} {text}" for _, level, text in all_headings)
        raise ToolError(f'no heading in this page matches "{section}". Its headings:\n{listed}')
    start, level, text = matches[0]
    end = next((index for index, other_level, _ in all_headings if index > start and other_level <= level), len(lines))
    return start, end, text


def read_google_doc(page: str, guide: str = "", section: str = "", start_line: int = 1, max_lines: int = READ_LINES_DEFAULT) -> str:
    found_guide, file_name = find_saved_page(page, guide)
    saved_page = saved_pages_by_file_name(found_guide).get(file_name)
    lines = (found_guide.folder / file_name).read_text(encoding="utf-8").splitlines()
    max_lines = min(max(max_lines, 1), READ_LINES_MAX)

    first, end, heading = 0, len(lines), ""
    if section.strip():
        first, end, heading = section_range(lines, section)
    first = max(first, start_line - 1)
    if first >= end:
        raise ToolError(f"start_line {start_line} is past the end ({end} lines{' of that section' if heading else ''})")
    last = min(end, first + max_lines)

    title = saved_page.title if saved_page else file_name
    source = saved_page.page_url if saved_page else found_guide.home_url
    shown = f"lines {first + 1}–{last} of {len(lines)}"
    if heading:
        shown = f'section "{heading}", {shown}'
    if last < end:
        shown += f"; more follows: call again with start_line={last + 1}"
    header = [
        f"{repo_path(found_guide, file_name)}: {title}",
        f"source: {source} (Google LLC, CC BY 4.0)",
        shown,
        "---",
    ]
    return "\n".join(header + lines[first:last])


def without_marks(text: str) -> str:
    """Text without Markdown bold, italic and code marks, so a quote copied from the web page still matches."""
    return text.replace("*", "").replace("`", "")


def check_google_quote(page: str, quote: str, guide: str = "") -> str:
    found_guide, file_name = find_saved_page(page, guide)
    saved_page = saved_pages_by_file_name(found_guide).get(file_name)
    source = saved_page.page_url if saved_page else found_guide.home_url
    lines = (found_guide.folder / file_name).read_text(encoding="utf-8").splitlines()
    wanted = " ".join(without_marks(quote).split())
    if not wanted:
        raise ToolError("quote is empty")
    flat, line_at = "", []  # the page with whitespace collapsed, and the line each character came from
    for number, line in enumerate(lines, 1):
        words = " ".join(without_marks(line).split())
        if words:
            flat += (" " if flat else "") + words
            line_at.extend([number] * (len(words) + 1))
    where = repo_path(found_guide, file_name)
    position = flat.find(wanted)
    if position >= 0:
        return f"Found verbatim in {where} at line {line_at[position]}. source: {source}"
    answer = [f"Not found verbatim in {where} (whitespace collapsed, bold and code marks ignored, case-sensitive)."]
    position = flat.casefold().find(wanted.casefold())
    if position >= 0:
        answer.append(f"It matches ignoring case at line {line_at[position]}: {flat[position:position + len(wanted)]}")
    else:
        stripped = [" ".join(without_marks(line).split()) for line in lines]
        close = difflib.get_close_matches(wanted, [line for line in stripped if line], n=1, cutoff=0.6)
        if close:
            answer.append(f"Closest line, {stripped.index(close[0]) + 1}: {close[0]}")
    answer.append(f"source: {source}")
    return "\n".join(answer)


# --- list_google_docs -----------------------------------------------------------------------


def list_google_docs(guide: str = ALL_GUIDES) -> str:
    listings = []
    for selected in selected_guides(guide):
        pages = sync.read_saved_pages(selected)
        snapshot = sync.saved_snapshot_date(selected) or "unknown"
        lines = [
            f"## {selected.key}: {selected.title}",
            f"{len(pages)} pages in {repo_path(selected, '')}/, snapshot {snapshot}. Home: {selected.home_url}",
            f"Each page's address: {sync.SITE_ORIGIN}{selected.root_path}/ + its file name without .md, "
            f"with {sync.PATH_SEPARATOR_IN_FILE_NAME} read as /.",
        ]
        current_section = None
        for page in pages:
            if page.section != current_section:
                current_section = page.section
                lines.append(f"### {current_section}")
            lines.append(f"- {selected.file_name(page.path)}: {page.title}")
        listings.append("\n".join(lines))
    return "\n\n".join(listings)


# --- check and update jobs ------------------------------------------------------------------


@dataclass
class Job:
    job_id: str
    kind: str  # "check" or "update"
    guides: list[sync.Guide]
    started: str = field(default_factory=utc_now)
    state: str = "running"  # "running", "done" or "failed"
    progress: str = "starting"
    results: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""
    finished: str = ""
    finished_event: threading.Event = field(default_factory=threading.Event)

    @property
    def guide_keys(self) -> set[str]:
        return {guide.key for guide in self.guides}


EXIT_STATUS_BY_RESULT = {"current": 0, "saved": 0, "out_of_date": 1, "no_local_copy": 1, "fetch_failed": 2}


def check_message(check: sync.GuideCheck) -> str:
    """What the check found, in the words the script prints, plus how to update the copy."""
    guide = check.guide
    if check.is_current:
        return "No changes: the local copy matches Google's current guide."
    if not check.has_local_copy:
        finding = "No local copy yet."
    elif check.comparison.upstream_changed:
        finding = f"Google changed the guide. Their notes: {guide.change_notes}"
    else:
        finding = "The local files differ from SHA256SUMS or the README.md the script would write."
    return f'{finding} To update the copy, call update_google_docs with guide "{guide.key}", then review: git diff {repo_path(guide, "")}'


def check_result(check: sync.GuideCheck) -> dict[str, Any]:
    comparison = check.comparison
    fetched_titles = check.titles_by_file_name
    saved_titles = {name: page.title for name, page in saved_pages_by_file_name(check.guide).items()}

    def titled(names: list[str], titles: dict[str, str]) -> list[dict[str, str]]:
        return [{"file": name, "title": titles.get(name, "")} for name in names]

    def unavailable(kind: str) -> list[dict[str, str]]:
        return [{"url": item.url, "reason": item.reason} for item in check.unavailable if item.kind == kind]

    if check.is_current:
        status = "current"
    else:
        status = "out_of_date" if check.has_local_copy else "no_local_copy"
    return {
        "guide": check.guide.key,
        "title": check.guide.title,
        "status": status,
        "pages_fetched": len(check.pages),
        "changed": titled(comparison.changed, fetched_titles),
        "new": titled(comparison.added, fetched_titles),
        "removed": titled(comparison.removed, saved_titles),
        "nav": comparison.navigation_changed,  # page titles, sections or order changed
        "readme_out_of_date": comparison.readme_out_of_date,
        "local": comparison.edited_locally,  # files that differ from SHA256SUMS here
        "no_md": unavailable("no-md"),  # these three are listed on every run and are not changes
        "dead": unavailable("dead"),
        "moved": unavailable("moved"),
        "message": check_message(check),
    }


def run_guide(job: Job, guide: sync.Guide) -> dict[str, Any]:
    def record_progress(_: sync.Guide, fetched: int, known: int) -> None:
        job.progress = f"{guide.key}: fetched {fetched} of {known} pages found so far"

    try:
        check = sync.check_guide(guide, record_progress)
    except sync.FetchError as error:
        return {"guide": guide.key, "title": guide.title, "status": "fetch_failed", "message": f"could not fetch the guide: {error}"}
    result = check_result(check)
    if job.kind == "update" and not check.is_current:
        job.progress = f"{guide.key}: saving"
        sync.save_check(check)
        result["status"] = "saved"
        result["message"] = f"Saved {len(check.contents)} pages. Review with: git diff {repo_path(guide, '')}"
    return result


def run_job(job: Job) -> None:
    try:
        for guide in job.guides:
            job.results.append(run_guide(job, guide))
        if job.kind == "update" and any(result["status"] == "saved" for result in job.results):
            job.progress = "rebuilding the vectors for search by meaning"
            try:
                job.results.append({"vectors": f"rebuilt: {vectors.build()} pieces"})
            except Exception as error:  # the update itself succeeded; say the vectors are stale
                job.results.append({"vectors": f"not rebuilt ({error}); run python3 vectors.py"})
        job.state = "done"
    except Exception as error:  # a bug or a disk problem: report it on the job instead of losing it with the thread
        job.error = f"{type(error).__name__}: {error}"
        job.state = "failed"
        traceback.print_exc(file=sys.stderr)
    finally:
        job.progress = ""
        job.finished = utc_now()
        job.finished_event.set()


class JobRegistry:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._numbers = count(1)

    def start(self, kind: str, guide: str) -> Job:
        """Start a job, or return the same job when it is already running; refuse to overlap another."""
        guides = selected_guides(guide)
        keys = {selected.key for selected in guides}
        with self._lock:
            for job in self._jobs.values():
                if job.state == "running" and job.guide_keys & keys:
                    if job.kind == kind and job.guide_keys == keys:
                        return job
                    raise ToolError(
                        f"job {job.job_id} ({job.kind} of {', '.join(sorted(job.guide_keys))}) is still running; "
                        "wait for it with google_docs_job, then try again"
                    )
            job = Job(f"{kind}-{guide}-{next(self._numbers)}", kind, guides)
            self._jobs[job.job_id] = job
        threading.Thread(target=run_job, args=(job,), name=job.job_id, daemon=True).start()
        return job

    def wait_for_running_updates(self) -> None:
        for job in self.all():
            if job.kind == "update":
                job.finished_event.wait()

    def get(self, job_id: str) -> Job:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            known = ", ".join(self._jobs) or "none"
            raise ToolError(f"no job {job_id!r} in this server process (jobs: {known}); jobs end when the server restarts")
        return job

    def all(self) -> list[Job]:
        with self._lock:
            return list(self._jobs.values())


JOBS = JobRegistry()
CLIENT_GONE = threading.Event()  # set when stdin closes, so calls stop waiting on jobs


def wait_for_job(job: Job, wait_seconds: int) -> None:
    deadline = time.monotonic() + min(max(wait_seconds, 0), JOB_WAIT_MAX_SECONDS)
    while not CLIENT_GONE.is_set() and (remaining := deadline - time.monotonic()) > 0:
        if job.finished_event.wait(min(remaining, 0.5)):
            return


def job_report(job: Job, wait_seconds: int) -> str:
    wait_for_job(job, wait_seconds)
    report: dict[str, Any] = {
        "job": job.job_id,
        "kind": job.kind,
        "guides": [guide.key for guide in job.guides],
        "state": job.state,
        "started": job.started,
    }
    if job.state == "running":
        report["progress"] = job.progress
        report["next"] = f'still running; call google_docs_job with job_id "{job.job_id}" to wait for the result'
    else:
        report["finished"] = job.finished
        if job.state == "failed":
            report["error"] = job.error
        else:
            report["exit_status"] = max(EXIT_STATUS_BY_RESULT[result["status"]] for result in job.results if "status" in result)
    report["results"] = job.results
    return json.dumps(report, indent=2, ensure_ascii=False)


def check_google_docs(guide: str = ALL_GUIDES, wait_seconds: int = JOB_WAIT_DEFAULT_SECONDS) -> str:
    return job_report(JOBS.start("check", guide), wait_seconds)


def update_google_docs(guide: str, wait_seconds: int = JOB_WAIT_DEFAULT_SECONDS) -> str:
    if guide == ALL_GUIDES:
        raise ToolError(f"update one guide at a time: {', '.join(GUIDE_KEYS)}")
    return job_report(JOBS.start("update", guide), wait_seconds)


def google_docs_job(job_id: str = "", wait_seconds: int = JOB_WAIT_DEFAULT_SECONDS) -> str:
    if job_id:
        return job_report(JOBS.get(job_id), wait_seconds)
    jobs = JOBS.all()
    if not jobs:
        return "No jobs in this server process yet. Start one with check_google_docs."
    return "\n".join(f"{job.job_id}: {job.state}, started {job.started}" for job in jobs)


# --- tool definitions -----------------------------------------------------------------------


@dataclass(frozen=True)
class Tool:
    name: str
    title: str
    description: str
    properties: dict[str, dict[str, Any]]
    required: tuple[str, ...]
    function: Callable[..., str]
    read_only: bool = True
    open_world: bool = False  # reaches developers.google.com

    @property
    def definition(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": self.properties,
                "required": list(self.required),
                "additionalProperties": False,
            },
            "annotations": {
                "title": self.title,
                "readOnlyHint": self.read_only,
                "destructiveHint": not self.read_only,
                "idempotentHint": True,
                "openWorldHint": self.open_world,
            },
        }


def guide_property(description: str, allow_all: bool = True) -> dict[str, Any]:
    choices = [*GUIDE_KEYS, ALL_GUIDES] if allow_all else GUIDE_KEYS
    return {"type": "string", "enum": choices, "description": description}


WAIT_PROPERTY = {
    "type": "integer",
    "minimum": 0,
    "maximum": JOB_WAIT_MAX_SECONDS,
    "default": JOB_WAIT_DEFAULT_SECONDS,
    "description": f"seconds to wait for the job to finish before returning its progress (default {JOB_WAIT_DEFAULT_SECONDS})",
}

TOOLS = {
    tool.name: tool
    for tool in (
        Tool(
            "search_google_docs",
            "Search Google's docs",
            "Search the saved copies of Google's developer documentation style guide (style), Search Central "
            "SEO docs (seo) and crawling infrastructure docs (crawling: robots.txt, Googlebot, crawl budget). "
            "Matches the query as a case-insensitive phrase on one line; a multi-word query that finds nothing "
            "is retried as every word on one line. Returns repo file:line hits grouped by page, each page with its "
            "title and developers.google.com source URL; pages whose title matches come first. Then lists the 5 sections "
            "closest in meaning to the query (local embedding model), with path, heading and line range for read_google_doc.",
            {
                "query": {"type": "string", "description": "word or phrase to find, such as robots.txt or noindex"},
                "guide": guide_property("which guide to search (default all)") | {"default": ALL_GUIDES},
                "max_results": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": SEARCH_RESULTS_MAX,
                    "default": SEARCH_RESULTS_DEFAULT,
                    "description": f"most matching lines to show, at most {LINES_SHOWN_PER_PAGE} per page (default {SEARCH_RESULTS_DEFAULT})",
                },
            },
            ("query",),
            search_google_docs,
        ),
        Tool(
            "read_google_doc",
            "Read a Google doc page",
            "Return one saved page verbatim as Markdown, or one section of it, with its source URL. `page` can be "
            "a file name from search or list (robots-txt--robots-txt-spec.md), a repo path, or the page's "
            f"developers.google.com address. Long pages come back {READ_LINES_DEFAULT} lines at a time; the header "
            "says where to continue.",
            {
                "page": {"type": "string", "description": "file name, repo path or developers.google.com address of the page"},
                "guide": guide_property("the page's guide, when a bare file name is in more than one", allow_all=False),
                "section": {"type": "string", "description": "heading text of the one section to return (exact, else the first heading containing it)"},
                "start_line": {"type": "integer", "minimum": 1, "default": 1, "description": "first line to return (1 is the top of the page)"},
                "max_lines": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": READ_LINES_MAX,
                    "default": READ_LINES_DEFAULT,
                    "description": f"most lines to return (default {READ_LINES_DEFAULT})",
                },
            },
            ("page",),
            read_google_doc,
        ),
        Tool(
            "check_google_quote",
            "Check a quote against a Google doc page",
            "Say whether `quote` appears verbatim (case-sensitive, any run of whitespace counts as one space, so a "
            "quote may span lines) in one saved page, with the line it starts on and the source URL. When it doesn't, "
            "shows a case-insensitive match or the closest line so the quote can be corrected. `page` is given as "
            "for read_google_doc.",
            {
                "page": {"type": "string", "description": "file name, repo path or developers.google.com address of the page"},
                "quote": {"type": "string", "description": "the exact words to look for"},
                "guide": guide_property("the page's guide, when a bare file name is in more than one", allow_all=False),
            },
            ("page", "quote"),
            check_google_quote,
        ),
        Tool(
            "list_google_docs",
            "List Google doc pages",
            "List a saved guide's pages by section: file name and title, from the guide's README.md, with its "
            "snapshot date and how file names map to developers.google.com addresses.",
            {"guide": guide_property("which guide to list (default all)") | {"default": ALL_GUIDES}},
            (),
            list_google_docs,
        ),
        Tool(
            "check_google_docs",
            "Check Google docs for changes",
            "Compare the saved copies with Google's live guides, page by page (SHA-256); writes nothing. Fetching "
            "takes about 15 seconds for crawling, 1 minute for style, 3 minutes for seo and 4 for all, so it runs "
            "as a background job: the call waits up to wait_seconds and returns the result, or the job id for "
            "google_docs_job. Per guide: status (current, out_of_date, no_local_copy, fetch_failed); pages changed, "
            "new and removed; nav (titles, sections or order changed); local (files edited here); and pages that "
            "can't be saved (no_md, dead, moved), which are listed on every run and are not changes.",
            {"guide": guide_property("which guide to check (default all)") | {"default": ALL_GUIDES}, "wait_seconds": WAIT_PROPERTY},
            (),
            check_google_docs,
            open_world=True,
        ),
        Tool(
            "update_google_docs",
            "Update a Google doc copy",
            "Save Google's current version of one guide over its local copy (pages, SHA256SUMS and README.md in "
            "guides/<guide>/), like `sync_google_docs.py --guide <guide> --save`. Writes "
            "files: run check_google_docs first and update only when the user asks. Runs as a background job like "
            "check_google_docs. Afterwards review the change with git diff.",
            {"guide": guide_property("which guide to update", allow_all=False), "wait_seconds": WAIT_PROPERTY},
            ("guide",),
            update_google_docs,
            read_only=False,
            open_world=True,
        ),
        Tool(
            "google_docs_job",
            "Google docs job status",
            "Progress and result of a check_google_docs or update_google_docs job, waiting up to wait_seconds for it "
            "to finish. Without job_id, lists this server's jobs. Jobs last only as long as the server process.",
            {"job_id": {"type": "string", "description": "the job id a check or update returned"}, "wait_seconds": WAIT_PROPERTY},
            (),
            google_docs_job,
        ),
    )
}


def bind_arguments(tool: Tool, arguments: Any) -> dict[str, Any]:
    """Check a call's arguments against the tool's schema; integers may arrive as JSON numbers or digit strings."""
    if not isinstance(arguments, dict):
        raise ToolError("arguments must be an object")
    unknown = sorted(set(arguments) - set(tool.properties))
    if unknown:
        raise ToolError(f"unknown argument {', '.join(unknown)}; {tool.name} takes {', '.join(tool.properties)}")
    missing = [name for name in tool.required if arguments.get(name) in (None, "")]
    if missing:
        raise ToolError(f"missing argument {', '.join(missing)}")
    bound = {}
    for name, value in arguments.items():
        schema = tool.properties[name]
        if value is None or (value == "" and name not in tool.required):
            continue  # an optional argument left empty takes its default
        if schema["type"] == "integer":
            if isinstance(value, float) and value.is_integer():
                value = int(value)
            elif isinstance(value, str) and value.strip().lstrip("-").isdigit():
                value = int(value)
            if not isinstance(value, int) or isinstance(value, bool):
                raise ToolError(f"{name} must be a whole number")
        elif not isinstance(value, str):
            raise ToolError(f"{name} must be a string")
        if "enum" in schema and value not in schema["enum"]:
            raise ToolError(f"{name} must be one of {', '.join(schema['enum'])}")
        bound[name] = value
    return bound


# --- MCP over stdio -------------------------------------------------------------------------


class StdioServer:
    def __init__(self) -> None:
        self._write_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=REQUEST_WORKERS, thread_name_prefix="request")

    def serve(self) -> None:
        for line in sys.stdin.buffer:
            if line.strip():
                self.receive(line)
        # The client has gone. Answer the calls already received (a call waiting on a job returns
        # its progress), let a running update finish writing its files, then exit without waiting
        # for checks.
        CLIENT_GONE.set()
        self._executor.shutdown(wait=True)
        JOBS.wait_for_running_updates()
        os._exit(0)

    def receive(self, line: bytes) -> None:
        try:
            message = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_error(None, PARSE_ERROR, "Parse error")
            return
        if not isinstance(message, dict) or "method" not in message:
            if not (isinstance(message, dict) and ("result" in message or "error" in message)):
                self.send_error(None, INVALID_REQUEST, "Invalid request")
            return  # otherwise a response; this server sends no requests, so there is nothing to match it with
        if "id" not in message:
            return  # a notification (initialized, cancelled): nothing to answer
        self._executor.submit(self.answer, message)

    def answer(self, request: dict[str, Any]) -> None:
        request_id = request["id"]
        try:
            result = self.dispatch(request["method"], request.get("params") or {})
        except RpcError as error:
            self.send_error(request_id, error.code, str(error))
        except Exception as error:
            traceback.print_exc(file=sys.stderr)
            self.send_error(request_id, INTERNAL_ERROR, f"{type(error).__name__}: {error}")
        else:
            self.send({"jsonrpc": "2.0", "id": request_id, "result": result})

    def dispatch(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method == "initialize":
            requested = params.get("protocolVersion")
            return {
                "protocolVersion": requested if requested in HANDSHAKE_PROTOCOL_VERSIONS else LATEST_PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": SERVER_INSTRUCTIONS,
            }
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": [tool.definition for tool in TOOLS.values()]}
        if method == "tools/call":
            tool = TOOLS.get(params.get("name"))
            if tool is None:
                raise RpcError(INVALID_PARAMS, f"Unknown tool: {params.get('name')}")
            try:
                text, is_error = tool.function(**bind_arguments(tool, params.get("arguments") or {})), False
            except ToolError as error:
                text, is_error = str(error), True
            return {"content": [{"type": "text", "text": text}], "isError": is_error}
        raise RpcError(METHOD_NOT_FOUND, f"Method not found: {method}")

    def send_error(self, request_id: Any, code: int, message: str) -> None:
        self.send({"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}})

    def send(self, message: dict[str, Any]) -> None:
        data = json.dumps(message, ensure_ascii=False).encode("utf-8") + b"\n"
        with self._write_lock:
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()


if __name__ == "__main__":
    StdioServer().serve()
