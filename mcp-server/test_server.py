"""Tests for the google_seo_and_style_guides MCP server, driven over stdio through launch.sh as a client would.

Run (standard library only):
    python3 -B -m unittest discover -s mcp-server
The check test reaches developers.google.com, so it runs only with GOOGLE_DOCS_NETWORK_TESTS=1.
"""
import contextlib
import functools
import http.server
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import page_check  # noqa: E402
import sync_google_docs  # noqa: E402

LAUNCHER = Path(__file__).resolve().parent / "launch.sh"
GOOD_PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lap siding</title><meta name="description" content="Lap siding for builders.">
<link rel="canonical" href="https://example.com/lap-siding"></head>
<body><a href="/specs">Siding specs</a> <a href="/"><img src="logo.png" alt="Home"></a></body></html>"""
BAD_PAGE = """<html><head><meta name="robots" content="noindex"><link rel="canonical" href="/a"><link rel="canonical" href="/b"></head>
<body><img src="x.png"><a href="javascript:go()">here</a><a href="/x"></a>
<script type="application/ld+json">{"@context": "https://schema.org", "@type": "Product"}</script></body></html>"""
ROBOTS_SPEC_URL = "https://developers.google.com/crawling/docs/robots-txt/robots-txt-spec"


class ServerSession:
    def __init__(self) -> None:
        self.process = subprocess.Popen([str(LAUNCHER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self.last_id = 0

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.last_id += 1
        message: dict[str, Any] = {"jsonrpc": "2.0", "id": self.last_id, "method": method}
        if params is not None:
            message["params"] = params
        self.process.stdin.write(json.dumps(message).encode() + b"\n")
        self.process.stdin.flush()
        response = json.loads(self.process.stdout.readline())
        assert response["id"] == self.last_id, response
        return response

    def call(self, tool: str, **arguments: Any) -> tuple[str, bool]:
        result = self.request("tools/call", {"name": tool, "arguments": arguments})["result"]
        return result["content"][0]["text"], result["isError"]

    def close(self) -> int:
        self.process.stdin.close()
        exit_status = self.process.wait(timeout=10)
        self.process.stdout.close()
        return exit_status


class GoogleDocsServerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.session = ServerSession()
        self.addCleanup(self.session.process.kill)
        initialized = self.session.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "0"}})
        self.initialize_result = initialized["result"]

    def tearDown(self) -> None:
        self.assertEqual(self.session.close(), 0, "the server should exit at once when the client closes stdin")

    def test_handshake(self) -> None:
        self.assertEqual(self.initialize_result["protocolVersion"], "2025-06-18")
        self.assertEqual(self.initialize_result["serverInfo"]["name"], "google_seo_and_style_guides")
        newer = self.session.request("initialize", {"protocolVersion": "2099-01-01"})["result"]
        self.assertEqual(newer["protocolVersion"], "2025-11-25")
        self.assertEqual(self.session.request("ping")["result"], {})

    def test_discover_probe_falls_back(self) -> None:
        self.assertEqual(self.session.request("server/discover")["error"]["code"], -32601)

    def test_tools_list(self) -> None:
        names = [tool["name"] for tool in self.session.request("tools/list")["result"]["tools"]]
        self.assertEqual(
            names,
            ["search_google_docs", "read_google_doc", "check_google_quote", "check_structured_data", "check_page", "google_docs_changes",
             "list_google_docs", "check_google_docs", "update_google_docs", "google_docs_job"],
        )

    def test_search_finds_robots_txt_in_crawling_pages(self) -> None:
        text, is_error = self.session.call("search_google_docs", query="robots.txt")
        self.assertFalse(is_error)
        self.assertIn("guides/crawling/robots-txt--", text)
        self.assertIn("source: https://developers.google.com/crawling/docs/robots-txt/", text)

    def test_search_retries_as_every_word(self) -> None:
        text, _ = self.session.call("search_google_docs", query="interprets Google", guide="crawling")
        self.assertIn("every word on one line", text)
        self.assertIn("robots-txt--robots-txt-spec.md", text)

    def test_search_without_hits(self) -> None:
        text, is_error = self.session.call("search_google_docs", query="zzqxv-not-a-word")
        self.assertFalse(is_error)
        self.assertTrue(text.startswith("No saved page"))

    def test_search_adds_meaning_block_or_says_it_is_off(self) -> None:
        text, is_error = self.session.call("search_google_docs", query="robots.txt", guide="crawling")
        self.assertFalse(is_error)
        self.assertIn("guides/crawling/robots-txt--", text)
        self.assertIn("[tier 1: Google Search's own rules]", text)  # when guides disagree, tier 1 wins
        vectors_built = (LAUNCHER.parent.parent / "vectors").exists()  # no folder: keyword only, quietly
        self.assertEqual(vectors_built, "Closest sections by meaning" in text or "Search by meaning is off:" in text, text[-300:])

    def test_quote_found_across_lines(self) -> None:
        text, is_error = self.session.call("check_google_quote", page=ROBOTS_SPEC_URL, quote="Google's crawlers download and parse the site's robots.txt file")
        self.assertFalse(is_error)
        self.assertTrue(text.startswith("Found verbatim"), text)
        self.assertIn("at line 7", text)
        self.assertIn(f"source: {ROBOTS_SPEC_URL}", text)

    def test_quote_not_found_shows_the_case_insensitive_match(self) -> None:
        text, is_error = self.session.call("check_google_quote", page="robots-txt--robots-txt-spec.md", quote="google's crawlers download and parse")
        self.assertFalse(is_error)
        self.assertTrue(text.startswith("Not found verbatim"), text)
        self.assertIn("Google's crawlers download and parse", text)

    def test_read_section_by_url(self) -> None:
        text, is_error = self.session.call("read_google_doc", page=ROBOTS_SPEC_URL, section="syntax")
        self.assertFalse(is_error)
        header, _, body = text.partition("\n---\n")
        self.assertIn('section "Syntax"', header)
        self.assertIn(f"source: {ROBOTS_SPEC_URL}", header)
        self.assertTrue(body.startswith("## Syntax"))
        self.assertIn("### `user-agent`", body)
        self.assertNotIn("## Grouping of lines and rules", body)

    def test_comment_in_code_block_is_not_a_heading(self) -> None:
        text, is_error = self.session.call("read_google_doc", page="robots-txt--robots-txt-spec.md", section="This robots.txt file controls")
        self.assertTrue(is_error)
        self.assertIn("## Syntax", text)

    def test_read_long_page_in_parts(self) -> None:
        text, _ = self.session.call("read_google_doc", page="style/word-list.md")
        self.assertIn("lines 1–400 of", text.splitlines()[2])
        self.assertIn("call again with start_line=401", text)
        text, _ = self.session.call("read_google_doc", page="/style/word-list", start_line=401, max_lines=10)
        self.assertIn("lines 401–410 of", text.splitlines()[2])

    def test_w3c_guide_is_labeled_and_quotable(self) -> None:
        text, is_error = self.session.call("read_google_doc", page="a11y-vocab/index.md", max_lines=5)
        self.assertFalse(is_error)
        self.assertIn("[W3C, not used by Google Search]", text.splitlines()[0])
        self.assertIn("source: https://www.w3.org/2021/a11y-discov-vocab/latest (W3C Community Group report", text)
        text, _ = self.session.call("check_google_quote", page="a11y-vocab/index.md", quote="The none value must not be set with any other feature value.")
        self.assertTrue(text.startswith("Found verbatim"), text)

    def test_read_only_saved_pages(self) -> None:
        for page in ("../../AGENTS.md", "README.md", "SHA256SUMS", "https://example.com/style/word-list"):
            with self.subTest(page=page):
                _, is_error = self.session.call("read_google_doc", page=page)
                self.assertTrue(is_error)

    def test_structured_data_article_missing_recommended(self) -> None:
        markup = '<html><script type="application/ld+json">{"@context": "https://schema.org", "@type": "NewsArticle", "headline": "Hi", "image": "a.jpg"}</script></html>'
        text, is_error = self.session.call("check_structured_data", markup=markup)
        self.assertFalse(is_error)
        self.assertIn("appearance--structured-data--article.md", text)
        self.assertIn("required, missing: none", text)
        self.assertIn("datePublished", text)
        self.assertIn("never invent a value", text)

    def test_structured_data_product_offer_missing_required(self) -> None:
        markup = json.dumps({"@context": "https://schema.org", "@graph": [
            {"@type": "Product", "name": "Lap", "offers": {"@type": "Offer", "priceCurrency": "USD"}},
            {"@type": "Thing", "name": "x"},
        ]})
        text, _ = self.session.call("check_structured_data", markup=markup)
        self.assertIn("nested Offer in offers", text)
        self.assertIn("one of price or priceSpecification.price", text)
        self.assertIn("Google documents no search feature for this type", text)
        text, is_error = self.session.call("check_structured_data", markup='{"@type": "Product",}')
        self.assertTrue(is_error)
        self.assertIn("not valid JSON", text)

    def test_structured_data_website_uses_site_names_page(self) -> None:
        text, _ = self.session.call("check_structured_data", markup='{"@type": "WebSite", "name": "Example"}')
        self.assertIn("appearance--site-names.md", text)
        self.assertIn("required, missing: url", text)
        self.assertIn("recommended, missing: alternateName", text)
        self.assertNotIn("Google documents no search feature for this type", text)

    def test_every_page_check_quote_is_in_its_page(self) -> None:
        for check in page_check.CHECKS:
            with self.subTest(check=check["name"]):
                text, is_error = self.session.call("check_google_quote", page=check["source"], quote=check["quote"])
                self.assertFalse(is_error, text)
                self.assertTrue(text.startswith("Found verbatim"), text)
                self.assertIn(f"source: {check['source']}", text)

    def test_check_good_page(self) -> None:
        text, is_error = self.session.call("check_page", html=GOOD_PAGE)
        self.assertFalse(is_error)
        self.assertTrue(text.startswith(f"{len(page_check.CHECKS)} checks: {len(page_check.CHECKS)} passed, 0 failed."), text)

    def test_check_bad_page(self) -> None:
        text, _ = self.session.call("check_page", html=BAD_PAGE)
        failed = {line.split(":")[0].removeprefix("FAIL ") for line in text.splitlines() if line.startswith("FAIL ")}
        self.assertEqual(failed, {"title", "meta description", "viewport", "html lang", "doctype", "charset", "no noindex", "one canonical",
                                  "canonical absolute", "img alt", "link href", "link text", "generic link text", "structured data"})
        self.assertIn("meant to stay out of Google", text)
        self.assertTrue(self.session.call("check_page", html="<p>", path="x.html")[1])

    def test_changes_newest_first(self) -> None:
        text, is_error = self.session.call("google_docs_changes", since="2026-11-11")
        self.assertFalse(is_error)
        newest = [line for line in (LAUNCHER.parent.parent / "CHANGES.md").read_text().splitlines() if line.startswith("## ")][-1]
        self.assertTrue(text.startswith(newest), text)  # CHANGES.md is appended to, so its last entry comes first
        self.assertIn("## 2026-11-11 lighthouse", text)
        self.assertTrue(self.session.call("google_docs_changes", since="last week")[1])

    def test_list_guide(self) -> None:
        text, _ = self.session.call("list_google_docs", guide="crawling")
        self.assertIn("## crawling: Google crawling infrastructure documentation", text)
        self.assertIn("### How to... › Use robots.txt to manage crawling", text)
        self.assertIn("- robots-txt--robots-txt-spec.md: How Google interprets the robots.txt specification", text)

    def test_bad_arguments(self) -> None:
        self.assertTrue(self.session.call("list_google_docs", guide="nope")[1])
        self.assertTrue(self.session.call("search_google_docs", query="x", colour="red")[1])
        self.assertTrue(self.session.call("search_google_docs", query="")[1])
        self.assertTrue(self.session.call("update_google_docs", guide="all")[1])
        self.assertTrue(self.session.call("google_docs_job", job_id="check-seo-99")[1])
        unknown = self.session.request("tools/call", {"name": "no_such_tool", "arguments": {}})
        self.assertEqual(unknown["error"]["code"], -32602)

    @unittest.skipUnless(os.environ.get("GOOGLE_DOCS_NETWORK_TESTS"), "reaches developers.google.com")
    def test_check_one_guide(self) -> None:
        text, _ = self.session.call("check_google_docs", guide="crawling", wait_seconds=120)
        report = json.loads(text)
        self.assertEqual(report["state"], "done")
        self.assertIn(report["results"][0]["status"], ("current", "out_of_date"))


class HtmlToMarkdownTest(unittest.TestCase):
    def test_converts_a_w3c_report(self) -> None:
        document = """<html><head><title>T</title><style>p {}</style></head><body>
<nav id="toc"><ol><li>Contents</li></ol></nav>
<section><h2><bdi>4.2</bdi> Vocabulary<a class="self-link" href="#v"></a></h2>
<p>Alt text, as in   the <a href="https://html.spec.whatwg.org/">[html]</a> <code>alt</code> attribute.</p>
<ul><li>one<ul><li>nested</li></ul></li></ul>
<aside class="example"><div class="marker"><a class="self-link" href="#e">Example <bdi>3</bdi></a></div>
<div class="ex-buttons"><button>JSON-LD</button></div><pre>{
   "a": 1
}</pre></aside><script>x()</script></section></body></html>"""
        self.assertEqual(
            sync_google_docs.html_to_markdown(document),
            "## 4.2 Vocabulary\n\n"
            "Alt text, as in the [[html]](https://html.spec.whatwg.org/) alt attribute.\n\n"
            "- one\n\n  - nested\n\nExample 3\n\n"
            '```\n{\n   "a": 1\n}\n```\n',
        )


class SiteCheckTest(unittest.TestCase):
    def test_site_check_follows_links(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "index.html").write_text(GOOD_PAGE.replace('href="/specs"', 'href="/second.html"'))
            Path(folder, "second.html").write_text(GOOD_PAGE.replace('href="/specs"', 'href="/"'))
            quiet = type("QuietHandler", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *args: None})
            handler = functools.partial(quiet, directory=folder)
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            start = f"http://127.0.0.1:{server.server_address[1]}/"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                page_check.check_site(start)
            server.shutdown()
            server.server_close()
        text = output.getvalue()
        self.assertIn(f"PASS {start}\n", text)
        self.assertIn(f"{start}second.html", text)
        self.assertIn("2 pages checked", text)


if __name__ == "__main__":
    unittest.main()
