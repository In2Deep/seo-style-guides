#!/usr/bin/env python3
"""Image checks on a built HTML page or a whole site, each tied to Google's own words.

Like page_check.py, every check names the saved guide page it comes from and quotes it exactly (a test
confirms each quote is in its page). Unlike it, this opens the image files: it reads their type and pixel size
from the first bytes (PNG, JPEG, GIF, BMP, WebP, AVIF, HEIC, TIFF, ICO, SVG). For a local HTML file, image
paths are read from disk; for a web address, every page of that site is checked and the images are fetched.
It reads only what the HTML says: no CSS, no JavaScript, no layout, so a size set in CSS is not seen.

Run: python3 image_check.py path/to/page.html|https://site/ [more ...]   (exit status 1 if any check fails)
"""
import re
import struct
import sys
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import Request, urlopen

import page_check
import structured_data
from page_check import FAILURES_SHOWN, LIGHTHOUSE, SEARCH, report

SUPPORTED = ("bmp", "gif", "jpeg", "png", "webp", "svg", "avif")  # Google Images, from the quote in CHECKS
EXTENSIONS = {"jpeg": (".jpg", ".jpeg", ".jpe", ".jfif"), "png": (".png",), "gif": (".gif",), "webp": (".webp",),
              "avif": (".avif",), "svg": (".svg",), "bmp": (".bmp",), "heic": (".heic", ".heif"),
              "tiff": (".tif", ".tiff"), "ico": (".ico",)}
GENERIC_NAME = re.compile(r"(img|image|images|dsc|dscn|dscf|pxl|mvimg|photo|pic|picture|screenshot|screen[-_ ]?shot"
                          r"|untitled|scan|file|placeholder)?[-_ ]?\d*([-_ ]\d+)*|[0-9a-f]{12,}", re.I)
FILE_NAME_ALT = re.compile(r"\S+\.(jpe?g|png|gif|webp|avif|svg|bmp|heic|tiff?)", re.I)
ICON_RELS = {"icon", "apple-touch-icon", "apple-touch-icon-precomposed"}  # the rel values Google's favicon page lists
ASPECT_THRESHOLD_PX = 2  # "more than a few pixels difference" (Lighthouse image aspect ratio audit)
OVERSIZE_FACTOR = 2  # a file up to twice its displayed width still serves sharp screens (2x)
MODERN_FORMAT_MIN_BYTES = 10_000  # ours, not Google's: smaller JPEG and PNG files gain too little to list
MIN_STRUCTURED_DATA_PIXELS = 50_000
FAVICON_MIN_PX, FAVICON_RECOMMENDED_PX = 8, 48
WEB_DEV = "https://web.dev/"


def image_facts(data: bytes) -> tuple[str, int, int]:
    """The file type and pixel width and height read from an image's first bytes; 0 x 0 when not known."""
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        return ("png", *struct.unpack(">II", data[16:24]))
    if data[:6] in (b"GIF87a", b"GIF89a") and len(data) >= 10:
        return ("gif", *struct.unpack("<HH", data[6:10]))
    if data.startswith(b"BM") and len(data) >= 26:
        width, height = struct.unpack("<ii", data[18:26])
        return "bmp", width, abs(height)
    if data.startswith(b"\xff\xd8"):
        return ("jpeg", *jpeg_size(data))
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ("webp", *webp_size(data))
    if data[4:8] == b"ftyp":  # ISO media file: AVIF or HEIC, told apart by the brands in the ftyp box
        brands = data[8:int.from_bytes(data[:4], "big")]
        kind = "avif" if b"avif" in brands or b"avis" in brands else "heic"
        sizes = [struct.unpack(">II", data[at + 8:at + 16]) for at in (m.start() for m in re.finditer(b"ispe", data))
                 if len(data) >= at + 16]
        return (kind, *max(sizes, key=lambda size: size[0] * size[1], default=(0, 0)))
    if data[:4] in (b"II*\x00", b"MM\x00*"):
        return "tiff", 0, 0
    if data[:4] == b"\x00\x00\x01\x00" and len(data) >= 22:
        entries = [data[6 + 16 * i:8 + 16 * i] for i in range(int.from_bytes(data[4:6], "little")) if len(data) >= 22 + 16 * i]
        return ("ico", *max(((w or 256, h or 256) for w, h in entries), default=(0, 0)))
    head = data[:20_000].decode("utf-8", "ignore")
    if re.search(r"<svg\b", head, re.I):
        return ("svg", *svg_size(head))
    return "unknown", 0, 0


def jpeg_size(data: bytes) -> tuple[int, int]:
    at = 2
    while at + 9 < len(data):
        if data[at] != 0xFF or data[at + 1] == 0xFF:
            at += 1
            continue
        marker = data[at + 1]
        if marker == 0x01 or 0xD0 <= marker <= 0xD8:
            at += 2
            continue
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):  # start of frame
            height, width = struct.unpack(">HH", data[at + 5:at + 9])
            return width, height
        at += 2 + int.from_bytes(data[at + 2:at + 4], "big")
    return 0, 0


def webp_size(data: bytes) -> tuple[int, int]:
    chunk = data[12:16]
    if chunk == b"VP8 " and len(data) >= 30:
        width, height = struct.unpack("<HH", data[26:30])
        return width & 0x3FFF, height & 0x3FFF
    if chunk == b"VP8L" and len(data) >= 25:
        b = data[21:25]
        return 1 + (b[0] | (b[1] & 0x3F) << 8), 1 + (b[1] >> 6 | b[2] << 2 | (b[3] & 0x0F) << 10)
    if chunk == b"VP8X" and len(data) >= 30:
        return 1 + int.from_bytes(data[24:27], "little"), 1 + int.from_bytes(data[27:30], "little")
    return 0, 0


def svg_size(head: str) -> tuple[int, int]:
    """The width and height attributes of the <svg> tag in pixels, else its viewBox; 0 x 0 when neither."""
    tag = re.search(r"<svg\b[^>]*>", head, re.I | re.S)
    attrs = dict(re.findall(r'([\w:-]+)\s*=\s*["\']([^"\']*)["\']', tag.group(0))) if tag else {}
    sizes = [re.fullmatch(r"\s*([\d.]+)\s*(px)?\s*", attrs.get(name, "")) for name in ("width", "height")]
    if all(sizes):
        return round(float(sizes[0].group(1))), round(float(sizes[1].group(1)))
    box = re.findall(r"[-\d.]+", attrs.get("viewBox", ""))
    return (round(float(box[2])), round(float(box[3]))) if len(box) == 4 else (0, 0)


class ImageParser(HTMLParser):
    """Collects every <img> (with the <source> elements of its <picture> and where it sits) and every favicon <link>."""

    def __init__(self, html: str):
        super().__init__(convert_charrefs=True)
        self.images, self.icons, self.picture = [], [], None
        self.depth = {"main": 0, "header": 0, "nav": 0}
        self.has_main = False
        self.feed(html)
        self.close()

    def handle_starttag(self, tag: str, attrs: list) -> None:
        values = {name: value or "" for name, value in attrs}
        line = self.getpos()[0]
        if tag in self.depth:
            self.depth[tag] += 1
            self.has_main |= tag == "main"
        elif tag == "picture":
            self.picture = []
        elif tag == "source" and self.picture is not None:
            self.picture.append(values)
        elif tag == "img":
            self.images.append({"attrs": values, "line": line, "sources": self.picture or [],
                                "in_main": self.depth["main"] > 0, "in_header": self.depth["header"] + self.depth["nav"] > 0})
        elif tag == "link" and ICON_RELS & set(values.get("rel", "").lower().split()) and values.get("href", "").strip():
            self.icons.append({"attrs": values, "line": line})

    def handle_endtag(self, tag: str) -> None:
        if tag in self.depth:
            self.depth[tag] = max(0, self.depth[tag] - 1)
        elif tag == "picture":
            self.picture = None


def srcset_urls(srcset: str) -> list[str]:
    return [candidate.split()[0] for candidate in srcset.split(",") if candidate.split()]


def number(value: str) -> int | None:
    return int(value) if value.strip().isdigit() else None


def listed(items: list[str]) -> str:
    more = len(items) - FAILURES_SHOWN
    return "; ".join(items[:FAILURES_SHOWN]) + (f"; and {more} more" if more > 0 else "")


def json_ld_images(value) -> list[str]:
    """Every address under an "image" key anywhere in the JSON-LD (a string, an ImageObject or a list of either)."""
    found = []
    if isinstance(value, dict):
        for key, inner in value.items():
            if key == "image":
                for image in inner if isinstance(inner, list) else [inner]:
                    url = image.get("url") or image.get("contentUrl") if isinstance(image, dict) else image
                    if isinstance(url, str) and url.strip():
                        found.append(url.strip())
            found += json_ld_images(inner)
    elif isinstance(value, list):
        for inner in value:
            found += json_ld_images(inner)
    return found


class ImagePage:
    """One page's images, with their files opened through a cache shared by every page of a run."""

    def __init__(self, html: str, base: str | Path, files: dict):
        self.parser, self.base, self.files = ImageParser(html), base, files
        try:
            self.json_ld = [url for item in structured_data.json_ld_items(html) for url in json_ld_images(item)]
        except ValueError:
            self.json_ld = []

    def file(self, src: str) -> dict:
        """kind, width, height and bytes of the file at src (as written in the page), or the error that stopped it."""
        src = src.strip()
        if src.startswith("data:"):
            return {"kind": "data", "width": 0, "height": 0, "bytes": 0, "error": ""}
        location = self.locate(src)
        if location not in self.files:
            try:
                if isinstance(location, Path):
                    data = location.read_bytes()
                else:
                    request = Request(location, headers={"User-Agent": page_check.USER_AGENT})
                    with urlopen(request, timeout=page_check.FETCH_TIMEOUT) as response:
                        data = response.read()
                kind, width, height = image_facts(data)
                self.files[location] = {"kind": kind, "width": width, "height": height, "bytes": len(data), "error": ""}
            except (OSError, ValueError) as error:
                status = f"HTTP {error.code}" if isinstance(error, HTTPError) else getattr(error, "strerror", None) or str(error)
                self.files[location] = {"kind": "", "width": 0, "height": 0, "bytes": 0, "error": status}
        return self.files[location]

    def locate(self, src: str) -> str | Path:
        address = urljoin(self.base, src) if isinstance(self.base, str) else src
        if urlsplit(address).scheme in ("http", "https"):
            return address
        path = unquote(urlsplit(src).path)
        folder = self.base.parent
        if path.startswith("/"):  # site-root path: the nearest folder above the page that has the file
            for root in (folder, *folder.parents):
                if (root / path.lstrip("/")).is_file():
                    return root / path.lstrip("/")
            return folder / path.lstrip("/")
        return folder / path

    def image_urls(self, image: dict) -> list[str]:
        """Every file the browser could pick for this <img>: src, srcset and its <picture> sources."""
        attrs = image["attrs"]
        urls = [attrs.get("src", "")] + srcset_urls(attrs.get("srcset", ""))
        for source in image["sources"]:
            urls += srcset_urls(source.get("srcset", ""))
        return list(dict.fromkeys(url.strip() for url in url_list(urls)))


def url_list(urls: list[str]) -> list[str]:
    return [url for url in urls if url.strip() and not url.strip().startswith("data:")]


def file_name(src: str) -> str:
    return PurePosixPath(unquote(urlsplit(src).path)).name


def kind_label(facts: dict) -> str:
    return "not an image file this checker recognises" if facts["kind"] == "unknown" else facts["kind"].upper()


def at(image: dict, text: str) -> str:
    return f"line {image['line']}: {text}"


def check_size_attributes(page: ImagePage) -> tuple[bool, str]:
    images = page.parser.images
    without = [at(e, e["attrs"].get("src", "")) for e in images
               if number(e["attrs"].get("width", "")) is None or number(e["attrs"].get("height", "")) is None]
    if without:
        return False, listed(without) + " (no width and height in pixels; a CSS aspect-ratio would not be seen here)"
    return True, f"{len(images)} <img>, all with width and height"


def check_supported_format(page: ImagePage) -> tuple[bool, str]:
    problems, count = [], 0
    for image in page.parser.images:
        for src in page.image_urls(image):
            count += 1
            facts = page.file(src)
            extension = PurePosixPath(file_name(src)).suffix.lower()
            if facts["error"]:
                problems.append(at(image, f"{src} could not be opened ({facts['error']})"))
            elif facts["kind"] not in SUPPORTED:
                problems.append(at(image, f"{src} is {kind_label(facts)}, which Google Images doesn't support"))
            elif extension in {e for exts in EXTENSIONS.values() for e in exts} and extension not in EXTENSIONS[facts["kind"]]:
                problems.append(at(image, f"{src} is {facts['kind'].upper()} inside, but its name ends in {extension}"))
    return (False, listed(problems)) if problems else (True, f"{count} image files, all in a supported format")


def check_file_names(page: ImagePage) -> tuple[bool, str]:
    generic = [at(image, src) for image in page.parser.images for src in page.image_urls(image)
               if file_name(src).split(".")[0] and GENERIC_NAME.fullmatch(file_name(src).split(".")[0])]
    return (False, listed(list(dict.fromkeys(generic)))) if generic else (True, "no generic file names")


def check_alt_text(page: ImagePage) -> tuple[bool, str]:
    bad = [at(e, f'alt="{e["attrs"]["alt"]}"') for e in page.parser.images
           if e["attrs"].get("alt", "").strip()
           and (FILE_NAME_ALT.fullmatch(e["attrs"]["alt"].strip()) or GENERIC_NAME.fullmatch(e["attrs"]["alt"].strip()))]
    if bad:
        return False, listed(bad) + " (a file name or a generic word, not a description)"
    return True, "no alt text that is a file name or a generic word (empty alt is right for decoration)"


def check_first_picture_not_lazy(page: ImagePage) -> tuple[bool, str]:
    parser = page.parser
    first = next((e for e in parser.images if (e["in_main"] if parser.has_main else not e["in_header"])), None)
    if first is None:
        return True, "no picture in the page's main content"
    where = "in <main>" if parser.has_main else "outside the header"
    if first["attrs"].get("loading", "").strip().lower() == "lazy":
        return False, at(first, f'the first picture {where}, {first["attrs"].get("src", "")}, has loading="lazy"; '
                                "if it is the largest thing on screen when the page opens, it must load right away")
    return True, at(first, f"the first picture {where} is not lazy loaded")


def check_aspect_ratio(page: ImagePage) -> tuple[bool, str]:
    wrong, count = [], 0
    for image in page.parser.images:
        width, height = number(image["attrs"].get("width", "")), number(image["attrs"].get("height", ""))
        facts = page.file(image["attrs"].get("src", "")) if image["attrs"].get("src", "").strip() else {}
        if not (width and height and facts.get("width") and facts.get("height")) or facts["kind"] == "svg":
            continue
        count += 1
        expected = width * facts["height"] / facts["width"]
        if abs(height - expected) > ASPECT_THRESHOLD_PX:
            wrong.append(at(image, f"{image['attrs']['src']} is {facts['width']}x{facts['height']} but set to "
                                   f"{width}x{height} (at width {width} its height would be {round(expected)})"))
    return (False, listed(wrong)) if wrong else (True, f"{count} pictures set to their file's shape")


def check_not_oversized(page: ImagePage) -> tuple[bool, str]:
    big, count = [], 0
    for image in page.parser.images:
        width = number(image["attrs"].get("width", ""))
        if not width or image["attrs"].get("srcset", "").strip() or image["sources"] or not image["attrs"].get("src", "").strip():
            continue
        facts = page.file(image["attrs"]["src"])
        if facts["kind"] in ("svg", "data") or not facts["width"]:
            continue
        count += 1
        if facts["width"] > OVERSIZE_FACTOR * width:
            big.append(at(image, f"{image['attrs']['src']} is {facts['width']} pixels wide, shown at {width} "
                                 f"({facts['bytes'] // 1000} KB); {OVERSIZE_FACTOR * width} wide would be enough"))
    return (False, listed(big)) if big else (True, f"{count} single-size pictures, none more than twice their width")


def check_modern_format(page: ImagePage) -> tuple[bool, str]:
    heavy = []
    for image in page.parser.images:
        offers_modern = any(source.get("type", "").lower() in ("image/webp", "image/avif") for source in image["sources"])
        for src in page.image_urls(image):
            facts = page.file(src)
            if not offers_modern and facts["kind"] in ("jpeg", "png") and facts["bytes"] >= MODERN_FORMAT_MIN_BYTES:
                heavy.append((facts["bytes"], at(image, f"{src} is {facts['kind'].upper()}, {facts['bytes'] // 1000} KB, "
                                                       "with no WebP or AVIF version")))
    heavy.sort(reverse=True)
    if heavy:
        return False, listed(list(dict.fromkeys(text for _, text in heavy))) + " (largest first)"
    return True, f"no JPEG or PNG of {MODERN_FORMAT_MIN_BYTES // 1000} KB or more without a WebP or AVIF version"


def check_structured_data_images(page: ImagePage) -> tuple[bool, str]:
    problems = []
    for src in page.json_ld:
        facts = page.file(src)
        if facts["error"]:
            problems.append(f"{src} could not be opened ({facts['error']})")
        elif facts["kind"] not in SUPPORTED:
            problems.append(f"{src} is {kind_label(facts)}, which Google Images doesn't support")
        elif facts["kind"] != "svg" and facts["width"] * facts["height"] < MIN_STRUCTURED_DATA_PIXELS:
            problems.append(f"{src} is {facts['width']}x{facts['height']}, "
                            f"{facts['width'] * facts['height']:,} pixels (under {MIN_STRUCTURED_DATA_PIXELS:,})")
    if problems:
        return False, listed(problems)
    return True, f"{len(page.json_ld)} JSON-LD images, all supported and big enough" if page.json_ld else "no JSON-LD image"


def check_favicon(page: ImagePage) -> tuple[bool, str]:
    icons, problems, notices = page.parser.icons, [], []
    for icon in icons:
        href = icon["attrs"]["href"].strip()
        facts = page.file(href)
        if facts["error"]:
            problems.append(at(icon, f"{href} could not be opened ({facts['error']})"))
        elif facts["kind"] == "unknown":
            problems.append(at(icon, f"{href} is {kind_label(facts)}"))
        elif facts["width"] != facts["height"]:
            problems.append(at(icon, f"{href} is {facts['width']}x{facts['height']}, not square"))
        elif facts["kind"] != "svg" and facts["width"] < FAVICON_MIN_PX:
            problems.append(at(icon, f"{href} is {facts['width']}x{facts['height']}"))
        elif facts["kind"] != "svg" and facts["width"] <= FAVICON_RECOMMENDED_PX:
            notices.append(f"{href} is {facts['width']}x{facts['height']}; Google recommends larger than "
                           f"{FAVICON_RECOMMENDED_PX}x{FAVICON_RECOMMENDED_PX}")
    if problems:
        return False, listed(problems)
    if not icons:
        return True, "no favicon <link> on this page"
    return True, f"{len(icons)} favicon links, all square" + (f". Notice: {'; '.join(notices)}" if notices else "")


CHECKS = [
    {"name": "width and height", "test": check_size_attributes, "source": WEB_DEV + "articles/optimize-cls",
     "quote": "Always include width and height size attributes on your images and video elements."},
    {"name": "supported format", "test": check_supported_format, "source": SEARCH + "appearance/google-images",
     "quote": "Google Search supports images referenced in the src attribute of img in the following file formats: BMP, GIF, JPEG, PNG, WebP, SVG, and AVIF. It's also a good idea to have the extension of your filename match with the file type."},
    {"name": "descriptive file names", "test": check_file_names, "source": SEARCH + "appearance/google-images",
     "quote": "Avoid using generic filenames like image1.jpg, pic.gif, 1.jpg when possible."},
    {"name": "alt text", "test": check_alt_text, "source": SEARCH + "appearance/google-images",
     "quote": "When writing alt text, focus on creating useful, information-rich content that uses keywords appropriately and is in context of the content of the page."},
    {"name": "first picture not lazy", "test": check_first_picture_not_lazy, "source": WEB_DEV + "articles/optimize-lcp",
     "quote": "Never lazy-load your LCP image, as that will always lead to unnecessary resource load delay, and will have a negative impact on LCP."},
    {"name": "aspect ratio", "test": check_aspect_ratio, "source": LIGHTHOUSE + "best-practices/image-aspect-ratio",
     "quote": "An image is set with explicit width and height values that differ from the source image's dimensions."},
    {"name": "not oversized", "test": check_not_oversized, "source": WEB_DEV + "learn/design/responsive-images",
     "quote": "However, if a user has a small screen and a low-bandwidth network, making them download the same size images as users with larger screens wastes data."},
    {"name": "modern format", "test": check_modern_format, "source": WEB_DEV + "learn/images/webp",
     "quote": "Google originally developed WebP as a lossy image format to supersede JPEG, one that was able to produce files smaller than a comparable-quality image file encoded as JPEG."},
    {"name": "structured data images", "test": check_structured_data_images, "source": SEARCH + "appearance/structured-data/article",
     "quote": "For best results, we recommend providing multiple high-resolution images (minimum of 50K pixels when multiplying width and height) with the following aspect ratios: 16x9, 4x3, and 1x1."},
    {"name": "favicon", "test": check_favicon, "source": SEARCH + "appearance/favicon-in-search",
     "quote": "Your favicon must be a square (1:1 aspect ratio) that's at least 8x8px."},
]


def run_checks(html: str, base: str | Path, files: dict | None = None) -> list[tuple[dict, bool, str]]:
    """base: the page's web address, or the path of the local HTML file (image paths are read relative to it)."""
    page = ImagePage(html, base, {} if files is None else files)
    return [(check, *check["test"](page)) for check in CHECKS]


def check_site(start: str) -> bool:
    """Checks the images of every page found under the start address; one block per page and a total. True if any failed."""
    files, passed_pages, failed_pages = {}, 0, 0
    for url, source, page in page_check.site_pages(start):
        if isinstance(page, str):
            print(f"FAIL {url} ({page}; linked from {source})\n")
            failed_pages += 1
            continue
        final, _, html = page
        results = run_checks(html, final, files)
        failed = [(check, found) for check, passed, found in results if not passed]
        failed_pages, passed_pages = failed_pages + bool(failed), passed_pages + (not failed)
        print(f"FAIL {url} ({len(failed)} failed)" if failed else f"PASS {url}")
        for check, found in failed:
            print(f"  FAIL {check['name']}: {found}", f'    Google: "{check["quote"]}"', f"    source: {check['source']}", sep="\n")
        print("".join(f"  NOTICE {check['name']}: {found}\n" for check, passed, found in results if passed and "Notice:" in found))
    print(f"{start}: {passed_pages + failed_pages} pages checked, {passed_pages} passed, {failed_pages} failed; "
          f"{len(files)} image files opened.\n")
    return failed_pages > 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__.strip().splitlines()[-1])
    any_failed = False
    for name in sys.argv[1:]:
        if name.startswith(("http://", "https://")):
            any_failed |= check_site(name)
            continue
        path = Path(name).resolve()
        results = run_checks(path.read_text(encoding="utf-8", errors="replace"), path)
        any_failed |= not all(passed for _, passed, _ in results)
        print(f"== {name}\n{report(results)}\n")
    sys.exit(1 if any_failed else 0)
