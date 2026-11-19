"""Tests for the google_seo_and_style_guides MCP server, driven over stdio through launch.sh as a client would.

Run (standard library only):
    python3 -B -m unittest discover -s mcp-server
The check test reaches developers.google.com, so it runs only with GOOGLE_DOCS_NETWORK_TESTS=1.
"""
import base64
import contextlib
import functools
import http.server
import io
import json
import os
import struct
import subprocess
import sys
import tempfile
import threading
import unittest
import zlib
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import image_check  # noqa: E402
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
        hidden = ('<html><!-- <script type="application/ld+json">{broken</script> -->'
                  '<script data-type="application/ld+json" type="text/plain">{"@type": "Recipe"}</script>'
                  '<template><script type="application/ld+json">{"@type": "Recipe"}</script></template></html>')
        text, _ = self.session.call("check_structured_data", markup=hidden)
        self.assertIn("No <script", text)  # a comment, another type and a <template> hold no JSON-LD
        for document in (markup, '{"@type":"NewsArticle","headline":"Hi","image":"a.jpg"}'):
            with self.subTest(document=document):
                text, is_error = self.session.call("check_structured_data", markup="\ufeff" + document)
                self.assertFalse(is_error, text)
                self.assertIn("Item 1: NewsArticle", text)

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
        for check in page_check.CHECKS + image_check.CHECKS:
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


class ImageCheckTest(unittest.TestCase):
    @staticmethod
    def png(width: int, height: int, padding: int = 0) -> bytes:
        def chunk(kind: bytes, body: bytes) -> bytes:
            return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))

        header = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        text = chunk(b"tEXt", b"Comment\0" + b"x" * padding) if padding else b""
        pixels = chunk(b"IDAT", zlib.compress(bytes((1 + width * 3) * height)))
        return b"\x89PNG\r\n\x1a\n" + header + text + pixels + chunk(b"IEND", b"")

    def test_bad_images_fail_every_check(self) -> None:
        def box(kind: bytes, body: bytes) -> bytes:
            return (8 + len(body)).to_bytes(4, "big") + kind + body

        def ispe(width: int, height: int) -> bytes:
            return box(b"ispe", bytes(4) + width.to_bytes(4, "big") + height.to_bytes(4, "big"))

        jpeg = (b"\xff\xd8\xff\xc0\x00\x0b\x08" + (300).to_bytes(2, "big") + (400).to_bytes(2, "big") + b"\x01\x01\x11\x00"
                + b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00" + bytes(4) + b"\xff\xd9")
        # primary item 1 is 8x8; item 2 (a bigger thumbnail, say) is 64x64: the primary item's size must win
        heic = box(b"ftyp", b"heic" + bytes(4) + b"mif1heic") + box(b"meta", bytes(4) + box(b"pitm", bytes(4) + b"\x00\x01") + box(
            b"iprp", box(b"ipco", ispe(8, 8) + ispe(64, 64)) + box(b"ipma", bytes(4) + (2).to_bytes(4, "big") + b"\x00\x01\x01\x01\x00\x02\x01\x02")))
        page = """<!DOCTYPE html><html lang="en"><head><link rel="icon" href="icon.png">
<script type="application/ld+json">{"@context": "https://schema.org", "@type": "Article", "image": "small.png"}</script></head>
<body><main><img src="IMG_1234.jpg" alt="IMG_1234.jpg" loading="lazy">
<img src="/wide.png" width="100" height="100" alt="A wide board"><img src="photo.heic" width="8" height="8" alt="A board">
<img src="https://[bad/x.png" srcset="blob:x 2x" width="\u00b2" height="1" alt="A broken address"></main></body></html>"""
        expected = {"width and height": "no width and height", "supported format": "is HEIC",
                    "descriptive file names": "IMG_1234.jpg", "alt text": 'alt="IMG_1234.jpg"',
                    "first picture not lazy": 'has loading="lazy"', "aspect ratio": "is 400x100 but set to 100x100",
                    "not oversized": "200 wide would be enough", "modern format": "with no WebP or AVIF version",
                    "structured data images": "under 50,000", "favicon": "not square"}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "pages").mkdir()
            (root / "pages" / "index.html").write_text(page)
            files = {"pages/IMG_1234.jpg": jpeg, "wide.png": self.png(400, 100, 20_000), "pages/photo.heic": heic,
                     "pages/icon.png": self.png(32, 16), "pages/small.png": self.png(100, 100)}
            for name, data in files.items():
                (root / name).write_bytes(data)
            results = image_check.run_checks(page, root / "pages" / "index.html")
        found = {check["name"]: (passed, text) for check, passed, text in results}
        self.assertEqual(set(found), set(expected))
        for name, words in expected.items():
            with self.subTest(check=name):
                self.assertFalse(found[name][0], found[name][1])
                self.assertIn(words, found[name][1])
        self.assertEqual(image_check.image_facts(jpeg), ("jpeg", 400, 300))
        self.assertEqual(image_check.image_facts(heic), ("heic", 8, 8))
        self.assertEqual(image_check.srcset_urls("board,closeup.png 2x, data:image/png;base64,AAAA 1x"),
                         ["board,closeup.png", "data:image/png;base64,AAAA"])

    def test_odd_input_is_read_like_a_browser(self) -> None:
        ic = image_check
        page = ('<base href="https://[bad/"><script type="application/ld+json">{"@type": "Article", "image": {"@id": []}}</script>'
                '<!-- <script type="application/ld+json">{broken</script> --><img src="gone.png" width="' + "9" * 5000 + '">')
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(len(ic.run_checks(page, Path(folder) / "index.html")), len(ic.CHECKS))  # no crash
        self.assertEqual(ic.ImagePage(page, Path("index.html"), {}).json_ld_errors, [])  # the commented-out block is not read
        self.assertEqual(ic.image_facts(b'<svg width="1e999" height="1"/>'), ("svg", 0, 0))
        self.assertEqual(ic.image_facts(b'<!-- <svg width="48" height="48"/> --><svg width="1in" height="2in"/>'), ("svg", 96, 192))
        self.assertEqual(ic.image_facts(b'<s:svg xmlns:s="http://www.w3.org/2000/svg" width="4" height="4"/>'), ("svg", 4, 4))
        self.assertEqual(ic.image_facts(b'<svg-thing width="4" height="4"/>')[0], "unknown")
        self.assertEqual(ic.image_facts(b"\x00\x00\x00\x14ftypavif\x00\x00\x00\x00avif\x00\x00\x00\x1cfreeispe" + bytes(4)
                                        + (300).to_bytes(4, "big") * 2), ("avif", 0, 0))  # no primary item: size unknown
        self.assertTrue(ic.cut_short("gif", b"GIF89a\x0a\x00\x0a\x00"))
        self.assertTrue(ic.cut_short("webp", b"RIFF\x88\x13\x00\x00WEBPVP8X" + bytes(18)))
        self.assertTrue(ic.cut_short("png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\x08tEXtIEND\xaeB`\x82" + bytes(4)))
        self.assertTrue(ic.cut_short("jpeg", b"\xff\xd8\xff\xe1\x00\x06\xff\xd9\x00\x00\xff\xda\x00\x02"))  # end marker only in EXIF
        self.assertTrue(ic.cut_short("ico", b"\x00\x00\x01\x00\x01\x00" + bytes(8) + (0).to_bytes(4, "little") + (22).to_bytes(4, "little")))
        for width, height, natural_width, natural_height, matches in [(320, 181, 1600, 900, True), (1000, 1010, 100, 100, False),
                                                                      (100, 102, 100, 100, False), (400, 185, 20, 10, False)]:
            self.assertEqual(ic.shapes_match(width, height, natural_width, natural_height), matches, (width, height))
        self.assertTrue(ic.shapes_match(1560, 402, 480, 123, responsive=True))
        parser = ic.ImageParser('<picture><source srcset="a.webp"><template><picture></picture></template><img src="a.png"></picture>')
        self.assertEqual(len(parser.images[0]["sources"]), 1)
        self.assertEqual(ic.srcset_urls("ignored.png 2q), selected.png 1x"), ["selected.png"])
        found, _ = ic.json_ld_images(['{"@type": "ProfilePage", "mainEntity": {"@type": "Person", "image": "me.png"}}',
                                      '{"@type": "ImageObject", "contentUrl": "board.jpg"}'])
        self.assertEqual(found, {"me.png": {"Person", "ProfilePage"}, "board.jpg": {"ImageObject"}})
        self.assertEqual([ic.name_stem(name) for name in ("image-cedar2024.png", "image.cedar2024.png",
                                                         "hero.BRhKKi9a_Z1wcXPz.webp", "hero-DiwrgTda.png", "hero.3f2a1b9c.png")],
                         ["image-cedar2024", "image.cedar2024", "hero", "hero", "hero"])
        for name, descriptive in (("image.cedar2024.png", True), ("IMG_1234.BRhKKi9a.jpg", False), ("IMG_1234.3f2a1b9c.jpg", False)):
            passed, detail = ic.check_file_names(ic.ImagePage(f'<img src="{name}">', Path("index.html"), {}))
            self.assertEqual(passed, descriptive, detail)  # a camera name stays generic behind a build hash
        self.assertIsNone(ic.FILE_NAME_ALT.fullmatch("The sign reads photo.jpg"))

    def test_walks_image_structure_before_accepting_end_markers(self) -> None:
        ic = image_check
        gif = (b"GIF89a" + struct.pack("<HHBBB", 64, 64, 0x80, 0, 0) + bytes(6)
               + b"," + struct.pack("<HHHHB", 0, 0, 64, 64, 0) + b"\x02\x03\x12\x3b\x45\x00\x3b")
        frame = b"\xff\xc2\x00\x0b\x08\x00\x20\x00\x40\x01\x01\x11\x00"
        scan = b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00\x12\xff\x00\x34"
        comment = b"\xff\xfe\x00\x08note\xff\xd9"
        jpeg = b"\xff\xd8" + frame + scan + comment + scan + b"\xff\xd9"
        bmp = (struct.pack("<2sIHHI", b"BM", 58, 0, 0, 54)
               + struct.pack("<IiiHHIIiiII", 40, 1, 1, 1, 24, 0, 4, 0, 0, 0, 0) + bytes(4))
        png = self.png(64, 64)
        for kind, intact, cut in (("gif", gif, gif[:-3]), ("jpeg", jpeg, b"\xff\xd8" + frame + scan + comment),
                                  ("bmp", bmp, bmp[:54]), ("png", png, png[:33] + png[-12:])):
            with self.subTest(kind=kind):
                self.assertFalse(ic.cut_short(kind, intact))
                self.assertTrue(ic.cut_short(kind, cut))
        self.assertEqual(ic.image_facts(jpeg), ("jpeg", 64, 32))
        self.assertEqual(ic.image_facts(b'<?xml version="1.0" encoding="x-not-a-codec"?><svg/>')[0], "unknown")

    def test_resolves_bases_and_caches_inline_fragments(self) -> None:
        ic = image_check
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            docs, assets = root / "docs", root / "assets"
            docs.mkdir()
            assets.mkdir()
            (root / "top.png").touch()
            (docs / "board.png").touch()
            (assets / "board.png").touch()
            for base, src, expected in (('<base href="/">', "top.png", root / "top.png"),
                                        ('<base href="/assets/?rev=2#x">', "board.png", assets / "board.png"),
                                        ('<base href=""><base href="/assets/">', "board.png", docs / "board.png")):
                with self.subTest(base=base):
                    page = ic.ImagePage(base, docs / "index.html", {})
                    self.assertEqual(page.locate(src), expected.resolve())
        page = ic.ImagePage('<base href="javascript:void(0)">', "https://site.invalid/docs/index.html", {})
        self.assertEqual(page.locate("board.png"), "https://site.invalid/docs/board.png")
        uri = "DATA:image/png;base64," + base64.b64encode(self.png(1, 1)).decode()
        self.assertEqual(page.file(uri + "#x")["kind"], "png")
        self.assertIs(page.file(uri + "#x"), page.file(uri + "#y"))
        self.assertEqual(len(page.files), 1)

    def test_responsive_source_dimensions_and_format_selection(self) -> None:
        ic = image_check
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "board.png").write_bytes(self.png(400, 300))
            (root / "wall.png").write_bytes(self.png(100, 100, 11_000))
            (root / "board.webp").write_bytes(base64.b64decode(
                "UklGRjgAAABXRUJQVlA4ICwAAADQAQCdASoCAAIAAgA0JaACdLoB+AADsAD+6zb//OJY6nd6Qf/MEr8g3hYAAA=="))
            fallback = '<img src="wall.png" width="100" height="100" alt="Wall">'
            html = '<picture><source srcset="board.png 0480w" width="200">' + fallback + '</picture>'
            page = ic.ImagePage(html, root / "index.html", {})
            self.assertEqual(ic.srcset_urls("board.png 0480w"), ["board.png"])
            passed, detail = ic.check_aspect_ratio(page)
            self.assertTrue(passed, detail)  # Chrome draws board.png at 200x150: with one side set, the file's shape holds
            self.assertTrue(detail.startswith("1 "), detail)
            page = ic.ImagePage('<picture><source srcset="board.png" width="200" height="50">' + fallback + '</picture>',
                                root / "index.html", {})
            self.assertIn("board.png is 400x300 but set to 200x50", ic.check_aspect_ratio(page)[1])
            for sources, expected in (
                    ('<source media="all" srcset="wall.png"><source srcset="board.webp">', False),
                    ('<source srcset="wall.png 1x, board.webp 2x">', False),
                    ('<source media="(min-width: 1000px)" srcset="board.webp">', True)):
                with self.subTest(sources=sources):
                    page = ic.ImagePage('<picture>' + sources + fallback + '</picture>', root / "index.html", {})
                    passed, detail = ic.check_modern_format(page)
                    self.assertEqual(passed, expected, detail)
                    if not expected:
                        self.assertIn("wall.png", detail)

    def test_json_ld_image_context_and_depth(self) -> None:
        ic = image_check
        profile = {"@type": "ProfilePage", "mainEntity": {"@id": "#person"}}
        person = {"@id": "#person", "@type": "Person", "image": "profile.png"}
        restaurant = {"@type": "Restaurant", "image": "restaurant.png"}
        scripts = ["[" * 1100 + "0" + "]" * 1100, json.dumps({"@graph": [profile, person, restaurant]})]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ("profile.png", "restaurant.png"):
                (root / name).write_bytes(self.png(100, 100))

            def check(scripts: list[str]) -> tuple[bool, str]:
                html = "".join(f'<script type="application/ld+json">{script}</script>' for script in scripts)
                return ic.check_structured_data_images(ic.ImagePage(html, root / "index.html", {}))

            passed, detail = check(scripts)
            self.assertFalse(passed, detail)
            self.assertIn("JSON-LD block 1", detail)
            self.assertIn("profile.png (ProfilePage)", detail)
            self.assertNotIn("restaurant.png", detail)
            carousel = {"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": 1, "item": restaurant}]}
            passed, detail = check([json.dumps(carousel)])
            self.assertFalse(passed, detail)
            self.assertIn("restaurant.png", detail)

if __name__ == "__main__":
    unittest.main()
