"""Tests for the google_seo_and_style_guides MCP server, driven over stdio through launch.sh as a client would.

Run (standard library only):
    python3 -B -m unittest discover -s mcp-server
The check test reaches developers.google.com, so it runs only with GOOGLE_DOCS_NETWORK_TESTS=1.
"""
import json
import os
import subprocess
import unittest
from pathlib import Path
from typing import Any

LAUNCHER = Path(__file__).resolve().parent / "launch.sh"
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
            ["search_google_docs", "read_google_doc", "check_google_quote", "list_google_docs", "check_google_docs", "update_google_docs", "google_docs_job"],
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
        self.assertTrue("Closest sections by meaning" in text or "Search by meaning is off:" in text, text[-300:])

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

    def test_read_only_saved_pages(self) -> None:
        for page in ("../../AGENTS.md", "README.md", "SHA256SUMS", "https://example.com/style/word-list"):
            with self.subTest(page=page):
                _, is_error = self.session.call("read_google_doc", page=page)
                self.assertTrue(is_error)

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


if __name__ == "__main__":
    unittest.main()
