#!/usr/bin/env python3
"""Mechanical checks on a built HTML page before it is deployed, each tied to Google's own words.

Every check names the saved guide page it comes from and quotes it exactly (a test confirms each
quote is in its page). Parses with html.parser; fetches nothing and runs no JavaScript.

A web address (http:// or https://) checks every page of that site found from its sitemap and links.

Run: python3 page_check.py path/to/page.html|https://site/ [more ...]   (exit status 1 if any check fails)
"""
import re
import sys
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urldefrag, urljoin, urlsplit
from urllib.request import Request, urlopen

import structured_data

LIGHTHOUSE = "https://developer.chrome.com/docs/lighthouse/"
SEARCH = "https://developers.google.com/search/docs/"
LEARN = "https://web.dev/learn/"
TEXT_KEPT = ("title", "a", "script")  # elements whose text the checks read
GENERIC_LINK_TEXT = {"click here", "click this", "go", "here", "this", "start", "right here", "more", "learn more"}
FAILURES_SHOWN = 10
CHARSET_BYTES = 1024
MAX_PAGES = 500
USER_AGENT = "seo-style-guides-page-check/1.0"
FETCH_TIMEOUT = 20
NOT_PAGES = tuple(".png .jpg .jpeg .gif .webp .avif .svg .ico .css .js .mjs .pdf .xml .woff .woff2 .ttf .otf .mp4 .webm .mov .zip".split())


class PageParser(HTMLParser):
    """Collects every start tag (name, attributes, line, raw text, end offset), the text of TEXT_KEPT elements and the doctype."""
    robots_header = ""  # the X-Robots-Tag HTTP header, when the page was fetched by address

    def __init__(self, html: str):
        super().__init__(convert_charrefs=True)
        self.line_starts = [0]
        for line in html.split("\n"):
            self.line_starts.append(self.line_starts[-1] + len(line) + 1)
        self.elements, self.open, self.doctype = [], [], None
        self.feed(html)
        self.close()

    def handle_decl(self, decl: str) -> None:
        if not self.elements and self.doctype is None:
            self.doctype = decl

    def handle_starttag(self, tag: str, attrs: list) -> None:
        line, column = self.getpos()
        raw = self.get_starttag_text() or f"<{tag}>"
        element = {"tag": tag, "attrs": {name: value or "" for name, value in attrs}, "line": line, "raw": raw,
                   "end": self.line_starts[line - 1] + column + len(raw), "text": "", "img_alts": []}
        self.elements.append(element)
        if tag == "img":
            for parent in self.open:
                parent["img_alts"].append(element["attrs"].get("alt", ""))
        if tag in TEXT_KEPT:
            self.open.append(element)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.open) - 1, -1, -1):
            if self.open[index]["tag"] == tag:
                del self.open[index:]
                break

    def handle_data(self, data: str) -> None:
        for element in self.open:
            element["text"] += data


def tags(page: PageParser, tag: str, **wanted: str) -> list[dict]:
    """Elements with this tag whose attributes equal the wanted values (case-insensitive)."""
    return [e for e in page.elements if e["tag"] == tag
            and all(e["attrs"].get(key, "").strip().lower() == value for key, value in wanted.items())]


def where(elements: list[dict]) -> str:
    shown = [f"line {e['line']}: {e['raw'][:160]}" for e in elements[:FAILURES_SHOWN]]
    more = len(elements) - len(shown)
    return "; ".join(shown) + (f"; and {more} more" if more > 0 else "")


def link_text(element: dict) -> str:
    return " ".join(element["text"].split())


def check_title(page, html):
    found = [e for e in tags(page, "title") if link_text(e)]
    return (True, f"<title>{link_text(found[0])}</title>") if found else (False, "no <title> with text")


def check_meta_description(page, html):
    found = tags(page, "meta", name="description")
    if found and found[0]["attrs"].get("content", "").strip():
        return True, found[0]["raw"]
    return False, where(found) if found else "no <meta name=\"description\">"


def check_viewport(page, html):
    found = tags(page, "meta", name="viewport")
    if found and "width=" in found[0]["attrs"].get("content", ""):
        return True, found[0]["raw"]
    return False, where(found) if found else "no <meta name=\"viewport\">"


def check_lang(page, html):
    found = tags(page, "html")
    if found and found[0]["attrs"].get("lang", "").strip():
        return True, found[0]["raw"]
    return False, where(found) if found else "no <html> tag"


def check_doctype(page, html):
    if page.doctype and page.doctype.strip().lower() == "doctype html":
        return True, f"<!{page.doctype}>"
    return False, f"<!{page.doctype}>" if page.doctype else "no <!DOCTYPE html> before the first tag"


def check_charset(page, html):
    found = [e for e in page.elements if e["tag"] == "meta" and "charset" in e["attrs"]]
    if found and len(html[:found[0]["end"]].encode("utf-8")) <= CHARSET_BYTES:
        return True, found[0]["raw"]
    return False, f"ends after byte {CHARSET_BYTES}: {where(found[:1])}" if found else "no <meta charset>"


def check_noindex(page, html):
    robots = [e for e in tags(page, "meta") if e["attrs"].get("name", "").lower() in ("robots", "googlebot")]
    blocked = [e for e in robots if {"noindex", "none"} & {word.strip() for word in e["attrs"].get("content", "").lower().split(",")}]
    if {"noindex", "none"} & set(re.split(r"[\s,:]+", page.robots_header.lower())):
        found = f"HTTP header X-Robots-Tag: {page.robots_header}" + (f"; {where(blocked)}" if blocked else "")
        return False, found + " (correct only on a page that is meant to stay out of Google)"
    if blocked:
        return False, where(blocked) + " (correct only on a page that is meant to stay out of Google)"
    return True, where(robots) if robots else "no robots meta tag"


def canonicals(page):
    return [e for e in tags(page, "link") if "canonical" in e["attrs"].get("rel", "").lower().split()]


def check_one_canonical(page, html):
    found = canonicals(page)
    return len(found) <= 1, where(found) if found else "no rel=canonical"


def check_canonical_absolute(page, html):
    found = canonicals(page)
    relative = [e for e in found if not (urlsplit(e["attrs"].get("href", "")).scheme in ("http", "https")
                                         and urlsplit(e["attrs"].get("href", "")).netloc)]
    return (False, where(relative)) if relative else (True, where(found) if found else "no rel=canonical")


def check_img_alt(page, html):
    images = tags(page, "img")
    without = [e for e in images if "alt" not in e["attrs"]]
    return (False, where(without)) if without else (True, f"{len(images)} <img>, all with alt")


def check_link_href(page, html):
    links = tags(page, "a")
    bad = [e for e in links if not e["attrs"].get("href", "").strip()
           or e["attrs"]["href"].strip().lower().startswith("javascript:")]
    return (False, where(bad)) if bad else (True, f"{len(links)} <a>, all with an href URL")


def check_link_text(page, html):
    links = tags(page, "a")
    empty = [e for e in links if not link_text(e) and not e["attrs"].get("title", "").strip()
             and not any(alt.strip() for alt in e["img_alts"])]
    if empty:
        return False, where(empty) + " (no text, no title attribute, no image alt)"
    return True, f"{len(links)} <a>, all with text, a title or an image alt"


def check_generic_link_text(page, html):
    generic = [e for e in tags(page, "a") if link_text(e).lower().strip(".!") in GENERIC_LINK_TEXT]
    return (False, where(generic)) if generic else (True, "no generic link text")


def check_json_ld(page, html):
    try:
        report = structured_data.check_structured_data(html)
    except ValueError as error:
        return False, str(error)
    if not report.startswith(structured_data.POLICY):
        return True, report
    lines = [line.strip() for line in report.splitlines()]
    required = [line for line in lines if line.startswith("required, missing:") and not line.endswith(": none")]
    recommended = [line for line in lines if line.startswith("recommended, missing:") and not line.endswith(": none")]
    found = "JSON-LD parses; " + ("; ".join(required) if required else "no required property missing")
    if recommended:
        found += f". Notice: {'; '.join(recommended)}. {structured_data.POLICY}"
    return not required, found + " (details: check_structured_data)"


CHECKS = [
    {"name": "title", "test": check_title, "source": SEARCH + "appearance/title-link",
     "quote": "Make sure every page on your site has a title specified in the <title> element."},
    {"name": "meta description", "test": check_meta_description, "source": LIGHTHOUSE + "seo/meta-description",
     "quote": "The audit fails if: - Your page doesn't have a <meta name=description> element. - The content attribute of the <meta name=description> element is empty."},
    {"name": "viewport", "test": check_viewport, "source": LIGHTHOUSE + "best-practices/viewport",
     "quote": 'A page fails the audit unless all of these conditions are met: - The document\'s <head> contains a <meta name="viewport"> tag. - The viewport meta tag contains a content attribute. - The content attribute\'s value includes the text width=.'},
    {"name": "html lang", "test": check_lang, "source": LEARN + "accessibility/more-html",
     "quote": "A valid language attribute should be added to every page as it signals the AT to which language it should use."},
    {"name": "doctype", "test": check_doctype, "source": LIGHTHOUSE + "best-practices/doctype",
     "quote": "Add the <!DOCTYPE html> declaration to the top of your HTML document"},
    {"name": "charset", "test": check_charset, "source": LIGHTHOUSE + "best-practices/charset",
     "quote": "Add a <meta charset> element within the first 1024 bytes of your HTML document. The element must be fully contained within the first 1024 bytes."},
    {"name": "no noindex", "test": check_noindex, "source": SEARCH + "crawling-indexing/robots-meta-tag",
     "quote": "Do not show this page, media, or resource in search results."},
    {"name": "one canonical", "test": check_one_canonical, "source": LIGHTHOUSE + "seo/canonical",
     "quote": "A page fails this audit if any of the following conditions are met: - There is more than one canonical link."},
    {"name": "canonical absolute", "test": check_canonical_absolute, "source": SEARCH + "crawling-indexing/consolidate-duplicate-urls",
     "quote": 'Use absolute paths rather than relative paths with the rel="canonical" link element.'},
    {"name": "img alt", "test": check_img_alt, "source": SEARCH + "appearance/google-images",
     "quote": "The most important attribute when it comes to providing more metadata for an image is the alt text"},
    {"name": "link href", "test": check_link_href, "source": SEARCH + "crawling-indexing/links-crawlable",
     "quote": "Google can't reliably extract URLs from <a> elements that don't have an href attribute or other tags that perform as links because of script events."},
    {"name": "link text", "test": check_link_text, "source": SEARCH + "crawling-indexing/links-crawlable",
     "quote": "Anchor text (also known as link text ) is the visible text of a link. This text tells people and Google something about the page you're linking to."},
    {"name": "generic link text", "test": check_generic_link_text, "source": LIGHTHOUSE + "seo/link-text",
     "quote": "Lighthouse flags the following generic link text:"},
    {"name": "structured data", "test": check_json_ld, "source": SEARCH + "appearance/structured-data/intro-structured-data",
     "quote": "You must include all the required properties for an object to be eligible for appearance in Google Search with enhanced display."},
]


def run_checks(html: str, robots_header: str = "") -> list[tuple[dict, bool, str]]:
    page = PageParser(html)
    page.robots_header = robots_header
    results = []
    for check in CHECKS:
        passed, found = check["test"](page, html)
        results.append((check, passed, found))
    return results


def report(results: list[tuple[dict, bool, str]]) -> str:
    failed = sum(not passed for _, passed, _ in results)
    lines = [f"{len(results)} checks: {len(results) - failed} passed, {failed} failed."]
    for check, passed, found in results:
        lines += [f"\n{'PASS' if passed else 'FAIL'} {check['name']}: {found}",
                  f'  Google: "{check["quote"]}"', f"  source: {check['source']}"]
    return "\n".join(lines)


def check_page(html: str) -> str:
    return report(run_checks(html))


def fetch(url: str) -> tuple[str, str, str, str]:
    """The final address, content type, X-Robots-Tag header and text of one web address."""
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=FETCH_TIMEOUT) as response:
        robots = ", ".join(response.headers.get_all("X-Robots-Tag") or [])
        text = response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")
        return response.geturl(), response.headers.get_content_type(), robots, text


def sitemap_locs(url: str) -> tuple[list[str], bool]:
    """The <loc> addresses in one sitemap file, and whether it is a sitemap index."""
    try:
        xml = fetch(url)[3]
    except (OSError, ValueError):
        return [], False
    return [unescape(loc.strip()) for loc in re.findall(r"<loc>(.*?)</loc>", xml, re.S)], "<sitemapindex" in xml


def sitemap_urls(origin: str) -> list[str]:
    """The page addresses in the site's sitemap, following a sitemap index one level."""
    for name in ("sitemap-index.xml", "sitemap.xml"):
        locs, is_index = sitemap_locs(f"{origin}/{name}")
        if locs:
            return [page for loc in locs for page in sitemap_locs(loc)[0]] if is_index else locs
    return []


def check_site(start: str) -> bool:
    """Checks every page found under the start address; prints one block per page and a total. True if any failed."""
    start = urldefrag(start)[0]
    parts = urlsplit(start)
    scope = parts.path.rstrip("/")
    order, linked_from, passed_pages, failed_pages, limit_reached = [], {}, 0, 0, False

    def add(url: str, source: str) -> None:
        nonlocal limit_reached
        url = urldefrag(url)[0]
        split = urlsplit(url)
        if (url in linked_from or split.scheme not in ("http", "https") or split.netloc != parts.netloc
                or not (split.path == scope or split.path.startswith(scope + "/")) or split.path.lower().endswith(NOT_PAGES)):
            return
        if len(order) >= MAX_PAGES:
            limit_reached = True
            return
        order.append(url)
        linked_from[url] = source

    add(start, "the address given")
    for url in sitemap_urls(f"{parts.scheme}://{parts.netloc}"):
        add(url, "the sitemap")
    for url in order:  # grows while links are followed
        try:
            final, kind, robots, html = fetch(url)
        except (OSError, ValueError) as error:
            status = f"HTTP {error.code}" if isinstance(error, HTTPError) else str(getattr(error, "reason", error))
            print(f"FAIL {url} (could not fetch: {status}; linked from {linked_from[url]})\n")
            failed_pages += 1
            continue
        if kind not in ("text/html", "application/xhtml+xml"):
            continue
        for element in tags(PageParser(html), "a"):
            add(urljoin(final, element["attrs"].get("href", "").strip()), url)
        results = run_checks(html, robots)
        failed = [(check, found) for check, passed, found in results if not passed]
        try:
            types = [name for item in structured_data.json_ld_items(html) for name in structured_data.item_types(item)]
        except ValueError:
            types = []
        failed_pages, passed_pages = failed_pages + bool(failed), passed_pages + (not failed)
        print(f"FAIL {url} ({len(failed)} failed)" if failed else f"PASS {url}", f"  JSON-LD: {', '.join(types) or 'none'}", sep="\n")
        for check, found in failed:
            print(f"  FAIL {check['name']}: {found}", f'    Google: "{check["quote"]}"', f"    source: {check['source']}", sep="\n")
        print("".join(f"  NOTICE {check['name']}: {found}\n" for check, passed, found in results if passed and "Notice:" in found))
    if limit_reached:
        print(f"Stopped at the limit of {MAX_PAGES} pages; more pages were found.")
    print(f"{start}: {passed_pages + failed_pages} pages checked, {passed_pages} passed, {failed_pages} failed.\n")
    return failed_pages > 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__.strip().splitlines()[-1])
    any_failed = False
    for name in sys.argv[1:]:
        if name.startswith(("http://", "https://")):
            any_failed |= check_site(name)
            continue
        results = run_checks(Path(name).read_text(encoding="utf-8", errors="replace"))
        any_failed |= not all(passed for _, passed, _ in results)
        print(f"== {name}\n{report(results)}\n")
    sys.exit(1 if any_failed else 0)
