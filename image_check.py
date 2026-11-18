#!/usr/bin/env python3
"""Image checks on a built HTML page or a whole site, each tied to Google's own words.

Like page_check.py, every check names the saved guide page it comes from and quotes it exactly (a test
confirms each quote is in its page). Unlike it, this opens the image files: it reads their type and pixel size
from the first bytes (PNG, JPEG, GIF, BMP, WebP, AVIF, HEIC, TIFF, ICO, PPM, SVG), at most MAX_IMAGE_BYTES of
each. For a local HTML file, image paths are read from disk; for a web address, every page of that site is
checked and the images are fetched. It reads only what the HTML says: no CSS, no JavaScript, no layout, so a
size set in CSS is not seen. Needs Python 3.10 or newer.

Run: python3 image_check.py path/to/page.html|https://site/ [more ...]   (exit status 1 if any check fails)
"""
import json
import re
import struct
import sys
from html.parser import HTMLParser
from http.client import HTTPException
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError
from urllib.parse import unquote, urldefrag, urljoin, urlsplit
from urllib.request import Request, urlopen

import page_check
import structured_data
from page_check import LIGHTHOUSE, SEARCH, report

SUPPORTED = ("bmp", "gif", "jpeg", "png", "webp", "svg", "avif")  # Google Images, from the quote in CHECKS
FAVICON_FORMATS = ("bmp", "gif", "ico", "png", "jpeg", "ppm", "tiff")  # Google's favicon page, quoted in CHECKS
RASTER = ("bmp", "gif", "jpeg", "png", "webp", "avif", "heic", "tiff", "ico", "ppm")
EXTENSIONS = {"jpeg": (".jpg", ".jpeg", ".jpe", ".jfif"), "png": (".png",), "gif": (".gif",), "webp": (".webp",),
              "avif": (".avif",), "svg": (".svg",), "bmp": (".bmp",), "heic": (".heic", ".heif"),
              "tiff": (".tif", ".tiff"), "ico": (".ico",), "ppm": (".ppm", ".pgm", ".pbm", ".pnm")}
AVIF_BRANDS = {b"avif", b"avis"}
HEIC_BRANDS = {b"heic", b"heix", b"heim", b"heis", b"hevc", b"hevx", b"mif1", b"msf1"}
GENERIC_NAME = re.compile(r"(img|image|images|dsc|dscn|dscf|pxl|mvimg|photo|pic|picture|screenshot|screen[-_ ]?shot"
                          r"|untitled|scan|file|placeholder)?[-_ ]?\d*([-_ ]\d+)*|[0-9a-f]{12,}", re.I)
BUILD_HASH = re.compile(r"[.-](?=[\w]*\d)(?=[\w]*[A-Za-z])\w{8,}$")  # "hero.BRhKKi9a_Z1wcXPz": the part a build tool adds
IMAGE_SUFFIX = re.compile(r".*\.(jpe?g|png|gif|webp|avif|svg|bmp|heic|heif|tiff?|ico)", re.I | re.S)
ICON_RELS = {"icon", "apple-touch-icon", "apple-touch-icon-precomposed"}  # the rel values Google's favicon page lists
SIZE_RULE_TYPES = {"Article", "NewsArticle", "BlogPosting", "Event", "LocalBusiness", "Product", "Recipe"}  # pages that give the 50K rule
SVG_UNITS = {"": 1, "px": 1, "in": 96, "cm": 96 / 2.54, "mm": 96 / 25.4, "pt": 4 / 3, "pc": 16}
MAX_IMAGE_BYTES = 30_000_000
ASPECT_THRESHOLD_PX = 2  # Lighthouse: the smaller projected side must be within less than 2 px
OVERSIZE_FACTOR = 2  # a file up to twice its displayed width still serves sharp screens (2x)
MODERN_FORMAT_MIN_BYTES = 10_000  # ours, not Google's: smaller JPEG and PNG files gain too little to list
MIN_STRUCTURED_DATA_PIXELS = 50_000
FAVICON_MIN_PX, FAVICON_RECOMMENDED_PX = 8, 48
WEB_DEV = "https://web.dev/"


def image_facts(data: bytes) -> tuple[str, int, int]:
    """The file type and pixel width and height read from an image's first bytes; 0 x 0 when not known."""
    if data.startswith(b"\x89PNG\r\n\x1a\n") and data[12:16] == b"IHDR" and len(data) >= 24:
        return ("png", *struct.unpack(">II", data[16:24]))
    if data[:6] in (b"GIF87a", b"GIF89a") and len(data) >= 10:
        return ("gif", *struct.unpack("<HH", data[6:10]))
    if data.startswith(b"BM") and len(data) >= 26:
        if int.from_bytes(data[14:18], "little") == 12:  # BITMAPCOREHEADER: 16-bit sizes
            return ("bmp", *struct.unpack("<HH", data[18:22]))
        width, height = struct.unpack("<ii", data[18:26])
        return "bmp", width, abs(height)
    if data.startswith(b"\xff\xd8"):
        return ("jpeg", *jpeg_size(data))
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ("webp", *webp_size(data))
    if data[4:8] == b"ftyp":  # ISO media file: AVIF or HEIC by its brands, else something else (an MP4, say)
        box_end = min(int.from_bytes(data[:4], "big"), len(data))
        brands = {data[8:12]} | {data[at:at + 4] for at in range(16, box_end - 3, 4)}
        kind = "avif" if brands & AVIF_BRANDS else "heic" if brands & HEIC_BRANDS else "unknown"
        return (kind, *heif_size(data)) if kind != "unknown" else ("unknown", 0, 0)
    if data[:4] in (b"II*\x00", b"MM\x00*"):
        return ("tiff", *tiff_size(data))
    if data[:4] == b"\x00\x00\x01\x00" and len(data) >= 22:
        entries = [data[6 + 16 * i:8 + 16 * i] for i in range(int.from_bytes(data[4:6], "little")) if len(data) >= 22 + 16 * i]
        return ("ico", *max(((w or 256, h or 256) for w, h in entries), default=(0, 0)))
    netpbm = re.match(rb"P[1-6](?:\s|#[^\n]*\n)+(\d+)(?:\s|#[^\n]*\n)+(\d+)", data[:512])
    if netpbm:
        return "ppm", int(netpbm.group(1)), int(netpbm.group(2))
    head = data[:20_000].decode("utf-8", "ignore")
    if re.sub(r"<\?xml.*?\?>|<!--.*?-->|<!DOCTYPE[^>]*>", "", head, flags=re.S | re.I).lstrip("﻿ \t\r\n")[:4].lower() == "<svg":
        return ("svg", *svg_size(head))  # the document's root is <svg>, not an HTML page with an icon in it
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


def boxes(data: bytes, start: int, end: int):
    """(type, body start, box end) of each ISO media box from start to end."""
    at = start
    while at + 8 <= end:
        size, kind, head = int.from_bytes(data[at:at + 4], "big"), data[at + 4:at + 8], 8
        if size == 1:
            size, head = int.from_bytes(data[at + 8:at + 16], "big"), 16
        elif size == 0:
            size = end - at
        if size < head or at + size > end:
            return
        yield kind, at + head, at + size
        at += size


def heif_size(data: bytes) -> tuple[int, int]:
    """The size of the primary item (pitm), from the ispe property ipma gives it; else the largest ispe."""
    try:
        meta = next(((start, end) for kind, start, end in boxes(data, 0, len(data)) if kind == b"meta"), None)
        primary, properties, associations = None, [], {}
        for kind, start, end in boxes(data, meta[0] + 4, meta[1]) if meta else ():  # meta is a full box
            if kind == b"pitm":
                primary = int.from_bytes(data[start + 4:start + (6 if data[start] == 0 else 8)], "big")
            elif kind == b"iprp":
                for inner, inner_start, inner_end in boxes(data, start, end):
                    if inner == b"ipco":
                        properties = [(name, body) for name, body, _ in boxes(data, inner_start, inner_end)]
                    elif inner == b"ipma":
                        associations = ipma(data, inner_start)
        for index in associations.get(primary, []):
            if 0 < index <= len(properties) and properties[index - 1][0] == b"ispe":
                return struct.unpack(">II", data[properties[index - 1][1] + 4:properties[index - 1][1] + 12])
    except (IndexError, struct.error):
        pass
    sizes = [struct.unpack(">II", data[at + 8:at + 16]) for at in (m.start() for m in re.finditer(b"ispe", data))
             if len(data) >= at + 16]
    return max(sizes, key=lambda size: size[0] * size[1], default=(0, 0))


def ipma(data: bytes, at: int) -> dict[int, list[int]]:
    """item id -> the 1-based ipco indexes associated with it."""
    version, flags = data[at], int.from_bytes(data[at + 1:at + 4], "big")
    count, at, found = int.from_bytes(data[at + 4:at + 8], "big"), at + 8, {}
    for _ in range(count):
        id_bytes = 2 if version < 1 else 4
        item, at = int.from_bytes(data[at:at + id_bytes], "big"), at + id_bytes
        indexes, at = [], at + 1
        for _ in range(data[at - 1]):
            if flags & 1:
                indexes.append(int.from_bytes(data[at:at + 2], "big") & 0x7FFF)
                at += 2
            else:
                indexes.append(data[at] & 0x7F)
                at += 1
        found[item] = indexes
    return found


def tiff_size(data: bytes) -> tuple[int, int]:
    """ImageWidth (256) and ImageLength (257) from the first IFD."""
    order = "<" if data[:2] == b"II" else ">"
    try:
        ifd = struct.unpack(order + "I", data[4:8])[0]
        found = {}
        for i in range(struct.unpack(order + "H", data[ifd:ifd + 2])[0]):
            entry = data[ifd + 2 + 12 * i:ifd + 14 + 12 * i]
            tag, kind = struct.unpack(order + "HH", entry[:4])
            if tag in (256, 257):
                found[tag] = struct.unpack(order + "H", entry[8:10])[0] if kind == 3 else struct.unpack(order + "I", entry[8:12])[0]
        return found.get(256, 0), found.get(257, 0)
    except struct.error:
        return 0, 0


def svg_size(head: str) -> tuple[int, int]:
    """width and height of the <svg> root in pixels (absolute units converted), else its viewBox size."""
    tag = re.search(r"<svg\b[^>]*>", head, re.I | re.S)
    attrs = dict(re.findall(r'([\w:-]+)\s*=\s*["\']([^"\']*)["\']', tag.group(0))) if tag else {}

    def length(name: str) -> float | None:
        found = re.fullmatch(r"\s*(\d*\.?\d+(?:e[-+]?\d+)?)\s*(px|in|cm|mm|pt|pc)?\s*", attrs.get(name, ""), re.I)
        return float(found.group(1)) * SVG_UNITS[(found.group(2) or "").lower()] if found else None

    width, height = length("width"), length("height")
    if width and height:
        return round(width), round(height)
    try:
        box = [float(part) for part in re.split(r"[\s,]+", attrs.get("viewBox", "").strip()) if part]
    except ValueError:
        box = []
    return (round(box[2]), round(box[3])) if len(box) == 4 and box[2] > 0 and box[3] > 0 else (0, 0)


def cut_short(kind: str, data: bytes) -> bool:
    """True when a file's own structure says it ends early (no full pixel decoding)."""
    if kind == "png":
        return b"IEND" not in data[-64:]
    if kind == "jpeg":
        return b"\xff\xd9" not in data
    if kind == "ico":
        entries = [data[6 + 16 * i:22 + 16 * i] for i in range(int.from_bytes(data[4:6], "little"))]
        return any(len(entry) < 16 or sum(struct.unpack("<II", entry[8:16])) > len(data) for entry in entries)
    return False


def open_image(location: str | Path) -> dict:
    """kind, width, height and bytes read from a local path, a web address or a data: URI, and any problem found."""
    facts = {"kind": "", "width": 0, "height": 0, "bytes": 0, "error": ""}
    try:
        if isinstance(location, Path):
            with location.open("rb") as stream:
                data, expected = stream.read(MAX_IMAGE_BYTES + 1), None
        else:
            request = Request(location, headers={"User-Agent": page_check.USER_AGENT})
            with urlopen(request, timeout=page_check.FETCH_TIMEOUT) as response:
                data, expected = response.read(MAX_IMAGE_BYTES + 1), response.headers.get("Content-Length")
    except (OSError, ValueError, HTTPException) as error:
        reason = f"HTTP {error.code}" if isinstance(error, HTTPError) else getattr(error, "strerror", None) or str(error) or type(error).__name__
        return facts | {"error": f"could not be opened ({reason})"}
    kind, width, height = image_facts(data)
    facts |= {"kind": kind, "width": width, "height": height, "bytes": len(data)}
    if len(data) > MAX_IMAGE_BYTES:
        facts["error"] = f"is over {MAX_IMAGE_BYTES // 1_000_000} MB; only its start was read"
    elif expected and expected.isdigit() and len(data) < int(expected):
        facts["error"] = f"is cut short ({len(data):,} of {int(expected):,} bytes arrived)"
    elif kind in RASTER and (width <= 0 or height <= 0):
        facts["error"] = f"is a {kind.upper()} whose pixel size can't be read"
    elif cut_short(kind, data):
        facts["error"] = f"is a {kind.upper()} that is cut short"
    return facts


class ImageParser(HTMLParser):
    """Collects every <img> (with the <source> elements of its <picture> and where it sits), every favicon <link>,
    and the first <base href>. Elements inside <template> are not part of the page and are skipped."""

    def __init__(self, html: str):
        super().__init__(convert_charrefs=True)
        self.images, self.icons, self.picture, self.base_href = [], [], None, None
        self.depth = {"main": 0, "header": 0, "nav": 0, "template": 0}
        self.feed(html)
        self.close()

    def handle_starttag(self, tag: str, attrs: list) -> None:
        values = {name: value or "" for name, value in attrs}
        line = self.getpos()[0]
        if tag in self.depth:
            self.depth[tag] += 1
        elif self.depth["template"]:
            return
        elif tag == "base" and self.base_href is None and values.get("href", "").strip():
            self.base_href = values["href"].strip()
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
    """The candidate addresses of a srcset, split as HTML does: an address runs to whitespace, and a comma only
    ends it at its end; descriptors run to the next comma outside parentheses."""
    urls, at, end = [], 0, len(srcset)
    while at < end:
        while at < end and (srcset[at].isspace() or srcset[at] == ","):
            at += 1
        start = at
        while at < end and not srcset[at].isspace():
            at += 1
        url = srcset[start:at]
        if url.endswith(","):
            url = url.rstrip(",")
        else:
            depth = 0
            while at < end and (srcset[at] != "," or depth):
                depth += (srcset[at] == "(") - (srcset[at] == ")")
                at += 1
        if url:
            urls.append(url)
    return urls


def number(value: str) -> int | None:
    """A positive whole number of pixels written in ASCII digits, else None."""
    value = value.strip()
    return int(value) if value.isascii() and value.isdigit() and int(value) > 0 else None


def listed(items: list[str]) -> str:
    return "; ".join(items)


def file_name(src: str) -> str:
    if src.startswith("data:"):
        return ""
    try:
        return PurePosixPath(unquote(urlsplit(src).path)).name
    except ValueError:
        return ""


def name_stem(src: str) -> str:
    """The file name without its last extension and without a build tool's hash."""
    return BUILD_HASH.sub("", PurePosixPath(file_name(src)).stem)


def shown(src: str) -> str:
    return src if not src.startswith("data:") else src[:40] + "..."


def kind_label(facts: dict) -> str:
    return "not an image file this checker recognises" if facts["kind"] == "unknown" else facts["kind"].upper()


def json_ld_images(html: str) -> tuple[dict[str, set], list[str]]:
    """Every image address in the page's JSON-LD with the @type of the item it is on (contentUrl before url,
    same-document @id references followed), and the blocks that don't parse. Each block is parsed on its own."""
    blocks, errors = [], []
    for number_in_page, match in enumerate(structured_data.LD_JSON_SCRIPT.finditer(html), 1):
        try:
            blocks.append(json.loads(match.group(1)))
        except ValueError as error:
            errors.append(f"JSON-LD block {number_in_page} doesn't parse ({error})")
    nodes, found = {}, {}

    def collect(value) -> None:
        if isinstance(value, dict):
            if isinstance(value.get("@id"), str) and len(value) > 1:
                nodes.setdefault(value["@id"], value)
            for inner in value.values():
                collect(inner)
        elif isinstance(value, list):
            for inner in value:
                collect(inner)

    def walk(value) -> None:
        if isinstance(value, dict):
            types = value.get("@type", [])
            types = {types} if isinstance(types, str) else {t for t in types if isinstance(t, str)} if isinstance(types, list) else set()
            images = value.get("image")
            for image in images if isinstance(images, list) else [] if images is None else [images]:
                if isinstance(image, dict) and set(image) == {"@id"}:
                    image = nodes.get(image["@id"], image)
                url = (image.get("contentUrl") or image.get("url")) if isinstance(image, dict) else image
                if isinstance(url, str) and url.strip():
                    found.setdefault(url.strip(), set()).update(types)
            for inner in value.values():
                walk(inner)
        elif isinstance(value, list):
            for inner in value:
                walk(inner)

    collect(blocks)
    walk(blocks)
    return found, errors


class ImagePage:
    """One page's images, with their files opened through a cache shared by every page of a run."""

    def __init__(self, html: str, base: str | Path, files: dict):
        self.parser, self.files = ImageParser(html), files
        self.json_ld, self.json_ld_errors = json_ld_images(html)
        href = self.parser.base_href or ""
        self.web_base, self.page_folder = None, None
        if isinstance(base, str):
            self.web_base = urljoin(base, href)
        elif urlsplit(href).scheme in ("http", "https"):
            self.web_base, self.page_folder, self.folder = href, base.parent, base.parent
        else:
            self.page_folder = self.folder = base.parent
            if href and not href.startswith("/"):
                joined = unquote(urlsplit(urljoin(base.resolve().as_uri(), href)).path)
                self.folder = Path(joined) if joined.endswith("/") else Path(joined).parent

    def file(self, src: str) -> dict:
        """kind, width, height, bytes and any problem of the file at src (as written in the page)."""
        try:
            location = self.locate(src.strip())
        except ValueError as error:
            reason = str(error) if str(error).startswith("is ") else f"is not an address it can read ({error})"
            return {"kind": "", "width": 0, "height": 0, "bytes": 0, "error": reason}
        if location not in self.files:
            self.files[location] = open_image(location)
        return self.files[location]

    def locate(self, src: str) -> str | Path:
        """A web address, a data: URI or a resolved local path; ValueError for anything else."""
        if src.startswith("data:"):
            return src
        if self.web_base is not None:
            address = urldefrag(urljoin(self.web_base, src))[0]
            if urlsplit(address).scheme not in ("http", "https"):
                raise ValueError(f"is not a web address it can open ({urlsplit(address).scheme}:)")
            return address
        parts = urlsplit(src)
        if parts.scheme in ("http", "https") or src.startswith("//"):
            return urldefrag(urljoin("https:", src))[0]
        if parts.scheme:
            raise ValueError(f"is not a web address or a file it can open ({parts.scheme}:)")
        path = unquote(parts.path)
        if path.startswith("/"):  # site-root path: the nearest folder above the page that has the file
            for root in (self.page_folder, *self.page_folder.parents):
                if (root / path.lstrip("/")).is_file():
                    return (root / path.lstrip("/")).resolve()
            return self.page_folder / path.lstrip("/")
        return (self.folder / path).resolve()

    def image_urls(self, image: dict) -> list[str]:
        """Every file the browser could pick for this <img>: src, srcset and its <picture> sources."""
        attrs = image["attrs"]
        urls = [attrs.get("src", "")] + srcset_urls(attrs.get("srcset", ""))
        for source in image["sources"]:
            urls += srcset_urls(source.get("srcset", ""))
        return list(dict.fromkeys(url.strip() for url in urls if url.strip()))


def at(item: dict, text: str) -> str:
    return f"line {item['line']}: {text}"


def check_size_attributes(page: ImagePage) -> tuple[bool, str]:
    images = page.parser.images
    without = [at(e, shown(e["attrs"].get("src", ""))) for e in images
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
                problems.append(at(image, f"{shown(src)} {facts['error']}"))
            elif facts["kind"] not in SUPPORTED:
                problems.append(at(image, f"{shown(src)} is {kind_label(facts)}, which Google Images doesn't support"))
            elif extension and extension not in EXTENSIONS[facts["kind"]]:
                problems.append(at(image, f"{src} is {facts['kind'].upper()} inside, but its name ends in {extension}"))
    return (False, listed(problems)) if problems else (True, f"{count} image files, all in a supported format")


def check_file_names(page: ImagePage) -> tuple[bool, str]:
    generic = [at(image, src) for image in page.parser.images for src in page.image_urls(image)
               if name_stem(src) and GENERIC_NAME.fullmatch(name_stem(src))]
    return (False, listed(list(dict.fromkeys(generic)))) if generic else (True, "no generic file names")


def check_alt_text(page: ImagePage) -> tuple[bool, str]:
    bad = []
    for image in page.parser.images:
        attrs = image["attrs"]
        if "alt" not in attrs:
            bad.append(at(image, f'{shown(attrs.get("src", ""))} has no alt attribute (alt="" is right for decoration)'))
            continue
        alt, src = attrs["alt"].strip(), attrs.get("src", "")
        if alt and (IMAGE_SUFFIX.fullmatch(alt) or alt.lower() in {file_name(src).lower(), name_stem(src).lower()}
                    or (re.search(r"[A-Za-z]", alt) and GENERIC_NAME.fullmatch(alt))):
            bad.append(at(image, f'alt="{attrs["alt"]}" (a file name or a generic word, not a description)'))
    return (False, listed(bad)) if bad else (True, "every <img> has alt text that isn't a file name or a generic word")


def check_first_picture_not_lazy(page: ImagePage) -> tuple[bool, str]:
    images = page.parser.images
    first = next((e for e in images if e["in_main"]), None)
    where = "in <main>"
    if first is None:
        first, where = next((e for e in images if not e["in_header"]), None), "outside the header and nav"
    if first is None:
        return True, "no picture outside the header and nav"
    if first["attrs"].get("loading", "").strip().lower() == "lazy":
        return False, at(first, f'the first picture {where}, {shown(first["attrs"].get("src", ""))}, has loading="lazy"; '
                                "if it is the largest thing on screen when the page opens, it must load right away")
    return True, at(first, f"the first picture {where} is not lazy loaded")


def shapes_match(width: int, height: int, natural_width: int, natural_height: int) -> bool:
    """Lighthouse's image-aspect-ratio rule (the smaller projected side within less than 2 px), measured at the
    file's own size, so a small srcset copy's rounding doesn't count as a wrong shape."""
    ratio = width / height
    target_height, target_width = natural_width / ratio, natural_height * ratio
    if target_height < target_width:
        return abs(target_height - natural_height) < ASPECT_THRESHOLD_PX
    return abs(target_width - natural_width) < ASPECT_THRESHOLD_PX


def check_aspect_ratio(page: ImagePage) -> tuple[bool, str]:
    wrong, count = [], 0
    for image in page.parser.images:
        attrs = image["attrs"]
        pairs = [(attrs, [attrs.get("src", "")] + srcset_urls(attrs.get("srcset", "")), False)]
        for source in image["sources"]:  # a <source> with its own width and height is measured against those
            own = number(source.get("width", "")) and number(source.get("height", ""))
            pairs.append((source if own else attrs, srcset_urls(source.get("srcset", "")), not own))
        for holder, urls, borrowed in pairs:
            width, height = number(holder.get("width", "")), number(holder.get("height", ""))
            for src in dict.fromkeys(url.strip() for url in urls if url.strip()):
                facts = page.file(src)
                if not (width and height) or facts["error"] or facts["kind"] not in RASTER or not (facts["width"] and facts["height"]):
                    continue
                count += 1
                if shapes_match(width, height, facts["width"], facts["height"]):
                    continue
                size = f"{shown(src)} is {facts['width']}x{facts['height']}"
                wrong.append(at(image, f"{size}, a different shape from the <img>'s {width}x{height}; give its <source> "
                                       "its own width and height" if borrowed else f"{size} but set to {width}x{height}"))
    return (False, listed(wrong)) if wrong else (True, f"{count} image files set to their own shape")


def check_not_oversized(page: ImagePage) -> tuple[bool, str]:
    big, count = [], 0
    for image in page.parser.images:
        width, src = number(image["attrs"].get("width", "")), image["attrs"].get("src", "").strip()
        if not width or image["attrs"].get("srcset", "").strip() or image["sources"] or not src:
            continue
        facts = page.file(src)
        if facts["error"] or facts["kind"] not in RASTER or not facts["width"]:
            continue
        count += 1
        if facts["width"] > OVERSIZE_FACTOR * width:
            big.append(at(image, f"{shown(src)} is {facts['width']} pixels wide, shown at {width} "
                                 f"({facts['bytes'] // 1000} KB); {OVERSIZE_FACTOR * width} wide would be enough"))
    return (False, listed(big)) if big else (True, f"{count} single-size pictures, none more than twice their width")


def check_modern_format(page: ImagePage) -> tuple[bool, str]:
    heavy = []
    for image in page.parser.images:  # a <source> counts when its file really is WebP or AVIF, whatever its type says
        offers_modern = any(page.file(url)["kind"] in ("webp", "avif")
                            for source in image["sources"] for url in srcset_urls(source.get("srcset", "")))
        for src in page.image_urls(image):
            facts = page.file(src)
            if not offers_modern and facts["kind"] in ("jpeg", "png") and facts["bytes"] >= MODERN_FORMAT_MIN_BYTES:
                heavy.append((facts["bytes"], at(image, f"{shown(src)} is {facts['kind'].upper()}, "
                                                       f"{facts['bytes'] // 1000} KB, with no WebP or AVIF version")))
    heavy.sort(reverse=True)
    if heavy:
        return False, listed(list(dict.fromkeys(text for _, text in heavy))) + " (largest first)"
    return True, f"no JPEG or PNG of {MODERN_FORMAT_MIN_BYTES // 1000} KB or more without a WebP or AVIF version"


def check_structured_data_images(page: ImagePage) -> tuple[bool, str]:
    problems = list(page.json_ld_errors)
    for src, types in page.json_ld.items():
        facts = page.file(src)
        sized_types = sorted(types & SIZE_RULE_TYPES)
        if facts["error"]:
            problems.append(f"{shown(src)} {facts['error']}")
        elif facts["kind"] not in SUPPORTED:
            problems.append(f"{shown(src)} is {kind_label(facts)}, which Google Images doesn't support")
        elif sized_types and facts["kind"] != "svg" and facts["width"] * facts["height"] < MIN_STRUCTURED_DATA_PIXELS:
            problems.append(f"{shown(src)} ({', '.join(sized_types)}) is {facts['width']}x{facts['height']}, "
                            f"{facts['width'] * facts['height']:,} pixels (under {MIN_STRUCTURED_DATA_PIXELS:,})")
    if problems:
        return False, listed(problems)
    return True, f"{len(page.json_ld)} JSON-LD images, all readable and big enough" if page.json_ld else "no JSON-LD image"


def check_favicon(page: ImagePage) -> tuple[bool, str]:
    icons, problems, notices, usable = page.parser.icons, [], [], 0
    for icon in icons:
        href = icon["attrs"]["href"].strip()
        facts = page.file(href)
        if facts["error"]:
            problems.append(at(icon, f"{shown(href)} {facts['error']}"))
        elif facts["kind"] not in FAVICON_FORMATS:
            continue  # another format (an SVG, say) is fine beside one Google reads
        elif facts["width"] != facts["height"]:
            problems.append(at(icon, f"{href} is {facts['width']}x{facts['height']}, not square"))
        elif facts["width"] < FAVICON_MIN_PX:
            problems.append(at(icon, f"{href} is {facts['width']}x{facts['height']}"))
        else:
            usable += 1
            if facts["width"] <= FAVICON_RECOMMENDED_PX:
                notices.append(f"{href} is {facts['width']}x{facts['height']}; Google recommends larger than "
                               f"{FAVICON_RECOMMENDED_PX}x{FAVICON_RECOMMENDED_PX}")
    if icons and not usable and not problems:
        problems.append("no favicon link in a format Google lists (BMP, GIF, ICO, PNG, JPEG, PPM, TIFF)")
    if problems:
        return False, listed(problems)
    if not icons:
        return True, "no favicon <link> on this page"
    return True, f"{usable} favicon links Google can use, all square" + (f". Notice: {'; '.join(notices)}" if notices else "")


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
     "quote": "Your favicon must be a square (1:1 aspect ratio) that's at least 8x8px. While the minimum size requirement is 8x8px, we recommend using a favicon that's larger than 48x48px so that it looks good on various surfaces. Google Search supports the following favicon file formats: BMP, GIF, ICO, PNG, JPEG, PPM, and TIFF."},
]


def run_checks(html: str, base: str | Path, files: dict | None = None) -> list[tuple[dict, bool, str]]:
    """base: the page's web address, or the path of the local HTML file (image paths are read relative to it)."""
    page = ImagePage(html, base, {} if files is None else files)
    return [(check, *check["test"](page)) for check in CHECKS]


def file_totals(files: dict) -> str:
    unopened = sum(facts["error"].startswith("could not be opened") for facts in files.values())
    return f"{len(files) - unopened} image files opened, {unopened} could not be opened"


def check_site(start: str, files: dict | None = None) -> bool:
    """Checks the images of every page found under the start address; one block per page and a total. True if any failed."""
    files = {} if files is None else files
    passed_pages = failed_pages = 0
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
    print(f"{start}: {passed_pages + failed_pages} pages checked, {passed_pages} passed, {failed_pages} failed; {file_totals(files)}.\n")
    return failed_pages > 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__.strip().splitlines()[-1])
    any_failed, shared_files = False, {}
    for name in sys.argv[1:]:
        if name.startswith(("http://", "https://")):
            any_failed |= check_site(name, shared_files)
            continue
        path = Path(name).resolve()
        results = run_checks(path.read_text(encoding="utf-8", errors="replace"), path, shared_files)
        any_failed |= not all(passed for _, passed, _ in results)
        print(f"== {name}\n{report(results)}\n")
    if len(sys.argv) > 2:
        print(f"In all: {file_totals(shared_files)}.")
    sys.exit(1 if any_failed else 0)
