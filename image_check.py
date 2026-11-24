#!/usr/bin/env python3
"""Image checks on a built HTML page or a whole site, each tied to Google's own words.

Like page_check.py, every check names the saved guide page it comes from and quotes it exactly (a test
confirms each quote is in its page). Unlike it, this opens the image files: it reads their type and pixel size
from the first bytes (PNG, JPEG, GIF, BMP, WebP, AVIF, HEIC, TIFF, ICO, PPM, SVG), at most MAX_IMAGE_BYTES of
each. For a local HTML file, image paths are read from disk; for a web address, every page of that site is
checked (or as many as --pages allows) and the images are fetched. It reads only what the HTML says: no CSS, no JavaScript, no layout, so a
size set in CSS is not seen. Needs Python 3.10 or newer.

Run: python3 image_check.py path/to/page.html|https://site/ [more ...] [--pages N]   (exit status 1 if any check fails)
"""
import json
import math
import re
import struct
import sys
from html.parser import HTMLParser
from xml.parsers import expat
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
BUILD_HASH = re.compile(r"""(  \.(?=\w*\d)(?=\w*[A-Z_])\w{8,}          # Astro, Parcel, webpack: hero.BRhKKi9a_Z1wcXPz
                               | -(?=[\w-]*[A-Z_])[\w-]{8}               # Vite and Rollup: hero-DiwrgTda
                               | [.-](?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{8,}  # a hex content hash: hero.3f2a1b9c
                             )$""", re.X)  # the part a build tool adds to a file name
FILE_NAME_ALT = re.compile(r"\S+\.(jpe?g|png|gif|webp|avif|svg|bmp|heic|heif|tiff?|ico)", re.I)  # alt that is a bare file name
ICON_RELS = {"icon", "apple-touch-icon", "apple-touch-icon-precomposed"}  # the rel values Google's favicon page lists
RESTAURANT_CAROUSEL = "Restaurant carousel"
SIZE_RULE_TYPES = {"Article", "NewsArticle", "BlogPosting", "Event", "Product", "Recipe", "ProfilePage", RESTAURANT_CAROUSEL}
BROWSER_TYPES = {"image/avif", "image/webp", "image/png", "image/apng", "image/jpeg", "image/gif", "image/svg+xml", "image/bmp",
                 "image/x-icon", "image/vnd.microsoft.icon"}  # a <source> with another type is skipped by the browser
SVG_UNITS = {"": 1, "px": 1, "in": 96, "cm": 96 / 2.54, "mm": 96 / 25.4, "pt": 4 / 3, "pc": 16}
SVG_NAMES = {"svg", "http://www.w3.org/2000/svg svg"}  # the root element, with no namespace or the SVG one
SVG_HEAD_BYTES = 64_000
MAX_PIXELS_SIDE = 1_000_000  # a width, height or SVG length beyond this is not taken as a size
MAX_IMAGE_BYTES = 30_000_000
ASPECT_THRESHOLD_PX = 2  # Lighthouse: the smaller projected side must be within less than 2 px
OVERSIZE_FACTOR = 2  # a file up to twice its displayed width still serves sharp screens (2x)
MODERN_FORMAT_MIN_BYTES = 10_000  # ours, not Google's: smaller JPEG and PNG files gain too little to list
MIN_STRUCTURED_DATA_PIXELS = 50_000
FAVICON_MIN_PX, FAVICON_RECOMMENDED_PX = 8, 48
WEB_DEV = "https://web.dev/"


NETPBM_SPACE = rb"(?:\s|#[^\r\n]*[\r\n])+"
NETPBM_SIZE = re.compile(rb"P[1-6]" + NETPBM_SPACE + rb"(\d{1,7})" + NETPBM_SPACE + rb"(\d{1,7})(?!\d)")
NETPBM_MAXVAL = re.compile(NETPBM_SPACE + rb"0*(\d{1,5})(?!\d)")
NETPBM_RASTER_START = re.compile(rb"(?:#[^\r\n]*)?\s")


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
    netpbm = NETPBM_SIZE.match(data, 0, 512)
    if netpbm:
        return "ppm", int(netpbm.group(1)), int(netpbm.group(2))
    root = svg_root(data)
    if root is not None:
        return ("svg", *svg_size(root))  # the document's root is <svg>, not an HTML page with an icon in it
    return "unknown", 0, 0


def jpeg_markers(data: bytes):
    """(marker, position) through the last scan, skipping length-delimited segments and stuffed scan bytes."""
    at, in_scan = 2, False
    while at + 1 < len(data):
        if in_scan:
            at = data.find(b"\xff", at)
            if at == -1:
                return
        elif data[at] != 0xFF:
            return
        while at + 1 < len(data) and data[at + 1] == 0xFF:
            at += 1
        if at + 1 >= len(data):
            return
        marker = data[at + 1]
        if marker == 0x01 or (in_scan and (marker == 0x00 or 0xD0 <= marker <= 0xD7)):
            at += 2
            continue
        if marker == 0xD9:
            yield marker, at
            return
        if marker == 0x00 or 0xD0 <= marker <= 0xD8 or at + 4 > len(data):
            return
        length = int.from_bytes(data[at + 2:at + 4], "big")
        segment_end = at + 2 + length
        minimum_length = 8 if marker == 0xDA else 2  # a scan header includes at least one component
        if length < minimum_length or segment_end > len(data):
            return
        yield marker, at
        at, in_scan = segment_end, marker == 0xDA


def jpeg_size(data: bytes) -> tuple[int, int]:
    for marker, at in jpeg_markers(data):
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):  # start of frame
            if int.from_bytes(data[at + 2:at + 4], "big") >= 11:
                height, width = struct.unpack_from(">HH", data, at + 5)
                return width, height
            break
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
    """The size of the primary item (pitm), from the ispe property ipma gives it; 0 x 0 when that can't be found."""
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
    return 0, 0


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


class FoundRoot(Exception):
    """Stops the XML parser at the first element."""


def svg_root(data: bytes) -> dict | None:
    """The attributes of the document's root element when it is <svg> (in the SVG namespace or none), else None.
    Read as XML from the first SVG_HEAD_BYTES, so a comment, a DOCTYPE or an <svg-thing> root is not taken for it."""
    parser, root = expat.ParserCreate(namespace_separator=" "), []

    def start(name: str, attrs: dict) -> None:
        root.append((name, attrs))
        raise FoundRoot

    parser.StartElementHandler = start
    try:
        parser.Parse(data[:SVG_HEAD_BYTES], False)
    except (FoundRoot, expat.ExpatError, LookupError, ValueError):
        pass
    return root[0][1] if root and root[0][0] in SVG_NAMES else None


def svg_size(attrs: dict) -> tuple[int, int]:
    """width and height of the <svg> root in pixels (absolute units converted), else its viewBox size."""
    def pixels(value: float) -> int | None:
        return round(value) if math.isfinite(value) and 0 < value < MAX_PIXELS_SIDE else None

    def length(name: str) -> int | None:
        found = re.fullmatch(r"\s*(\d*\.?\d+(?:e[-+]?\d+)?)\s*(px|in|cm|mm|pt|pc)?\s*", attrs.get(name, ""), re.I)
        return pixels(float(found.group(1)) * SVG_UNITS[(found.group(2) or "").lower()]) if found else None

    width, height = length("width"), length("height")
    if width and height:
        return width, height
    try:
        box = [float(part) for part in re.split(r"[\s,]+", attrs.get("viewBox", "").strip()) if part]
    except ValueError:
        box = []
    box_width, box_height = (pixels(box[2]), pixels(box[3])) if len(box) == 4 else (None, None)
    return (box_width, box_height) if box_width and box_height else (0, 0)


def gif_has_trailer(data: bytes) -> bool:
    """Follow color tables and sub-block lengths to the GIF trailer."""
    if len(data) < 13:
        return False
    at = 13  # header and logical screen descriptor
    if data[10] & 0x80:
        at += 3 * (2 << (data[10] & 7))  # global color table
    while at < len(data):
        block = data[at]
        at += 1
        if block == 0x3B:
            return True
        if block == 0x21:  # extension label before the sub-blocks
            at += 1
        elif block == 0x2C:  # image descriptor, optional color table, LZW code size
            if at + 9 >= len(data):
                return False
            flags = data[at + 8]
            at += 9
            if flags & 0x80:
                at += 3 * (2 << (flags & 7))
            at += 1  # skip the LZW code size before the sub-blocks
        else:
            return False
        while at < len(data):
            size = data[at]
            at += 1 + size
            if size == 0:
                break
    return False


def webp_has_image(data: bytes) -> bool:
    """Find a bounded image or animation-frame chunk inside the declared RIFF container."""
    end = 8 + int.from_bytes(data[4:8], "little")
    if end > len(data):
        return False
    header_sizes = {b"VP8 ": 10, b"VP8L": 5, b"ANMF": 16 + 8 + 5}  # ANMF also contains a bitstream chunk
    at, found = 12, False
    while at + 8 <= end:
        name, size = struct.unpack_from("<4sI", data, at)
        at += 8 + size + (size % 2)  # RIFF pads odd-sized chunks
        if at > end:
            return False
        if name in header_sizes and size > header_sizes[name]:
            found = True
    return found and at == end


def netpbm_has_raster(data: bytes) -> bool:
    """Check the byte count of the first raster in a binary PBM, PGM or PPM file."""
    dimensions = NETPBM_SIZE.match(data, 0, 512)
    if dimensions is None:
        return False
    width, height = map(int, dimensions.groups())
    at = dimensions.end()
    if data[1:2] == b"4":  # one bit per pixel, with each PBM row padded to a byte
        size = ((width + 7) // 8) * height
    else:
        maximum = NETPBM_MAXVAL.match(data, at, 512)
        max_value = int(maximum[1]) if maximum else 0
        if not 0 < max_value <= 65535:
            return False
        channels = 3 if data[1:2] == b"6" else 1
        size = width * height * channels * (2 if max_value >= 256 else 1)
        at = maximum.end()
    separator = NETPBM_RASTER_START.match(data, at, 512)
    return separator is not None and len(data) - separator.end() >= size


def cut_short(kind: str, data: bytes) -> bool:
    """True when a file's own structure says it ends early (no full pixel decoding)."""
    if kind == "png":  # require image data before a complete, empty IEND chunk
        if data[8:16] != b"\x00\x00\x00\rIHDR":
            return True
        at, found = 8, False
        while at + 12 <= len(data):
            size, name = struct.unpack_from(">I4s", data, at)
            at += 12 + size
            if at > len(data):
                return True
            if name == b"IEND":
                return size != 0 or not found
            found |= name == b"IDAT"
        return True
    if kind == "jpeg":
        saw_scan = False
        for marker, _ in jpeg_markers(data):
            if marker == 0xD9:
                return not saw_scan
            saw_scan |= marker == 0xDA
        return True
    if kind == "gif":
        return not gif_has_trailer(data)
    if kind == "webp":
        return not webp_has_image(data)
    if kind == "bmp":
        if len(data) < 26:
            return True
        size = int.from_bytes(data[2:6], "little") or len(data)
        offset, dib_size = struct.unpack_from("<II", data, 10)
        return dib_size < 12 or not 14 + dib_size <= offset < size <= len(data)
    if kind == "ico":
        count = int.from_bytes(data[4:6], "little")
        directory_end = 6 + 16 * count
        if not count or directory_end >= len(data):
            return True
        for at in range(6, directory_end, 16):
            size, offset = struct.unpack_from("<II", data, at + 8)
            if not size or offset < directory_end or offset + size > len(data):
                return True
    if kind == "ppm" and data[1:2] in (b"4", b"5", b"6"):
        return not netpbm_has_raster(data)
    return False


def is_data(src: str) -> bool:
    return src[:5].lower() == "data:"


def open_image(location: str | Path) -> dict:
    """kind, width, height and bytes read from a local path, a web address or a data: URI, and any problem found."""
    facts = {"kind": "", "width": 0, "height": 0, "bytes": 0, "error": ""}
    if not isinstance(location, Path) and is_data(location) and len(location) > MAX_IMAGE_BYTES * 4 // 3 + 1_000:
        return facts | {"error": f"is an inline data: image over {MAX_IMAGE_BYTES // 1_000_000} MB; it was not read"}
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
    elif expected and expected.isascii() and expected.isdigit() and len(expected) <= 15 and len(data) < int(expected):
        facts["error"] = f"is cut short ({len(data):,} of {int(expected):,} bytes arrived)"
    elif kind in RASTER and (width <= 0 or height <= 0):
        facts["error"] = f"is a {kind.upper()} whose pixel size can't be read"
    elif cut_short(kind, data):
        facts["error"] = f"is a {kind.upper()} that is cut short"
    return facts


class ImageParser(HTMLParser):
    """Collects every <img> (with the <source> elements of its <picture> and where it sits), every favicon <link>
    and the first <base href>. Elements inside <template> are not part of the page and are skipped, end tags
    included."""

    def __init__(self, html: str):
        super().__init__(convert_charrefs=True)
        self.images, self.icons, self.picture, self.base_href = [], [], None, None
        self.depth = {"main": 0, "header": 0, "nav": 0, "template": 0}
        self.feed(html)
        self.close()

    def handle_starttag(self, tag: str, attrs: list) -> None:
        values = {name: value or "" for name, value in attrs}
        line = self.getpos()[0]
        if tag == "template":
            self.depth["template"] += 1
        if self.depth["template"]:
            return
        if tag in self.depth:
            self.depth[tag] += 1
        elif tag == "base" and self.base_href is None and "href" in values:
            self.base_href = next((value or "").strip() for name, value in attrs if name == "href")
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
        if tag == "template":
            self.depth["template"] = max(0, self.depth["template"] - 1)
        elif self.depth["template"]:
            return
        elif tag in self.depth:
            self.depth[tag] = max(0, self.depth[tag] - 1)
        elif tag == "picture":
            self.picture = None


SRCSET_WHITESPACE = " \t\n\r\f"  # HTML ASCII whitespace
DESCRIPTOR = re.compile(r"0*[1-9]\d*[wh]|(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?x", re.ASCII)


def srcset_urls(srcset: str) -> list[str]:
    """The candidate addresses of a srcset, split as HTML does: an address runs to whitespace, and a comma only
    ends it at its end; descriptors run to the next comma outside parentheses. A candidate whose descriptors are
    not valid (one w or one x, h only beside w) is dropped, as the browser drops it."""
    urls, at, end = [], 0, len(srcset)
    while at < end:
        while at < end and (srcset[at] in SRCSET_WHITESPACE or srcset[at] == ","):
            at += 1
        start = at
        while at < end and srcset[at] not in SRCSET_WHITESPACE:
            at += 1
        url, descriptors = srcset[start:at], ""
        if url.endswith(","):
            url = url.rstrip(",")
        else:
            in_parens, descriptor_start = False, at
            while at < end and (srcset[at] != "," or in_parens):
                in_parens = srcset[at] == "(" or (in_parens and srcset[at] != ")")
                at += 1
            descriptors = srcset[descriptor_start:at]
        tokens = re.findall(r"[^ \t\n\r\f]+", descriptors)
        kinds = [token[-1] for token in tokens]
        valid = (all(DESCRIPTOR.fullmatch(token) for token in tokens) and len(set(kinds)) == len(kinds)
                 and not {"w", "x"} <= set(kinds) and ("h" not in kinds or "w" in kinds))
        if url and valid:
            urls.append(url)
    return urls


def number(value: str) -> int | None:
    """A positive whole number of pixels written in ASCII digits, else None."""
    value = value.strip()
    return int(value) if value.isascii() and value.isdigit() and 0 < len(value) <= 7 and int(value) > 0 else None


def listed(items: list[str]) -> str:
    return "; ".join(items)


def file_name(src: str) -> str:
    if is_data(src):
        return ""
    try:
        return PurePosixPath(unquote(urlsplit(src).path)).name
    except ValueError:
        return ""


def name_stem(src: str) -> str:
    """The file name without its last extension and without a build tool's hash."""
    return BUILD_HASH.sub("", PurePosixPath(file_name(src)).stem)


def shown(src: str) -> str:
    return src if not is_data(src) else src[:40] + "..."


def kind_label(facts: dict) -> str:
    return "not an image file this checker recognises" if facts["kind"] == "unknown" else facts["kind"].upper()


def json_ld_images(scripts: list[str]) -> tuple[dict[str, set[str]], list[str]]:
    """Image addresses with their owning types and feature contexts, plus errors from individual JSON-LD blocks."""
    objects, errors = [], []
    for number_in_page, script in enumerate(scripts, 1):
        try:
            value = json.loads(script.lstrip().removeprefix("\ufeff"))
            block_objects = list(structured_data.json_ld_objects(value))
        except RecursionError:
            errors.append(f"JSON-LD block {number_in_page} is too deeply nested")
        except ValueError as error:
            errors.append(f"JSON-LD block {number_in_page} doesn't parse ({error})")
        else:
            objects.extend(block_objects)

    nodes, found = {}, {}
    for value in objects:
        if isinstance(item_id := value.get("@id"), str):
            node = nodes.setdefault(item_id, {})
            for name, inner in value.items():
                node.setdefault(name, inner)

    def values(value) -> list:
        return value if isinstance(value, list) else [value]

    def node_key(value: dict) -> str | int:
        item_id = value.get("@id")
        return item_id if isinstance(item_id, str) else id(value)

    def resolve(value):
        if isinstance(value, dict) and isinstance(item_id := value.get("@id"), str):
            return nodes[item_id] | value
        return value

    profile_entities, carousel_items = set(), set()
    for value in objects:
        item = resolve(value)
        types = set(structured_data.item_types(item))
        if "ProfilePage" in types:
            profile_entities.update(node_key(entity) for entity in values(item.get("mainEntity")) if isinstance(entity, dict))
        if "ItemList" in types:
            for entry in values(item.get("itemListElement")):
                member = resolve(entry)
                if isinstance(member, dict) and "ListItem" in structured_data.item_types(member):
                    carousel_items.update(node_key(target) for target in values(member.get("item")) if isinstance(target, dict))

    def add(image, types: set[str]) -> None:
        image = resolve(image)
        url = (image.get("contentUrl") or image.get("url")) if isinstance(image, dict) else image
        if isinstance(url, str) and url.strip():
            found.setdefault(url.strip(), set()).update(types)

    for value in objects:
        types = set(structured_data.item_types(resolve(value)))
        key = node_key(value)
        if key in profile_entities:
            types.add("ProfilePage")
        if key in carousel_items and "Restaurant" in types:
            types.add(RESTAURANT_CAROUSEL)
        for image in values(value.get("image")):
            add(image, types)
        if "ImageObject" in types:
            add(value, types)
    return found, errors


class ImagePage:
    """One page's images, with their files opened through a cache shared by every page of a run."""

    def __init__(self, html: str, base: str | Path, files: dict):
        self.parser, self.files = ImageParser(html), files
        self.json_ld, self.json_ld_errors = json_ld_images(structured_data.ld_json_scripts(html))
        self.web_base = base if isinstance(base, str) else None
        self.page_folder = base.parent if isinstance(base, Path) else None
        self.local_base = base.resolve().as_uri() if isinstance(base, Path) else None
        href = self.parser.base_href
        if not href:
            return
        try:
            parts = urlsplit(href)
            if parts.scheme in ("javascript", "data"):
                return
            if self.web_base is not None or parts.scheme in ("http", "https") or (not parts.scheme and parts.netloc):
                address = urljoin(self.web_base or "https:", href)
                target = urlsplit(address)
                if target.scheme in ("http", "https"):
                    if not target.hostname:
                        return
                    _ = target.port  # validates the port before accepting the base URL
                self.web_base = address
            else:
                # Resolve each asset against a site-root base before looking for its file on disk.
                self.local_base = href if parts.path.startswith("/") else urljoin(self.local_base, href)
        except ValueError:
            pass  # Invalid bases use the document URL.

    def from_site_root(self, path: str) -> Path:
        """A site-root path (/x/y) as a local path: under the nearest folder above the page that has it."""
        relative = unquote(path).lstrip("/")
        for root in (self.page_folder, *self.page_folder.parents):
            if (root / relative).is_file():
                return (root / relative).resolve()
        return self.page_folder / relative

    def file(self, src: str) -> dict:
        """kind, width, height, bytes and any problem of the file at src (as written in the page)."""
        try:
            location = self.locate(src.strip())
        except (ValueError, OSError, RuntimeError) as error:
            reason = str(error) if str(error).startswith("is ") else f"is not an address it can read ({error})"
            return {"kind": "", "width": 0, "height": 0, "bytes": 0, "error": reason}
        if location not in self.files:
            self.files[location] = open_image(location)
        return self.files[location]

    def locate(self, src: str) -> str | Path:
        """A web address, a data: URI or a resolved local path; ValueError for anything else."""
        if is_data(src):
            inline = src.partition("#")[0]
            return inline if inline.startswith("data:") else "data:" + inline[5:]
        parts = urlsplit(src)
        if self.web_base is not None or parts.scheme in ("http", "https") or parts.netloc:
            address = urldefrag(urljoin(self.web_base or "https:", src))[0]
            scheme = urlsplit(address).scheme
            if scheme not in ("http", "https"):
                raise ValueError(f"is not a web address it can open ({scheme}:)")
            return address
        if parts.scheme:
            raise ValueError(f"is not a web address or a file it can open ({parts.scheme}:)")
        resolved = urlsplit(urljoin("/" if parts.path.startswith("/") else self.local_base, src))
        if not resolved.scheme:
            return self.from_site_root(resolved.path)
        if resolved.scheme != "file":
            raise ValueError(f"is not a web address or a file it can open ({resolved.scheme}:)")
        return Path(unquote(resolved.path)).resolve()

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
        if not image["attrs"].get("src", "").strip():
            problems.append(at(image, "an <img> with no src; Google recommends a src beside srcset and <picture>, "
                                      "for crawlers that don't read them"))
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
        if alt and (FILE_NAME_ALT.fullmatch(alt) or alt.lower() in {file_name(src).lower(), name_stem(src).lower()}
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


def shapes_match(width: int, height: int, natural_width: int, natural_height: int, *, responsive: bool = False) -> bool:
    """Lighthouse's image-aspect-ratio rule: the file's shape projected onto the HTML width and height, the smaller
    side within less than 2 px. A smaller srcset candidate can also differ by less than one file pixel from rounding."""
    ratio = natural_width / natural_height
    target_height, target_width = width / ratio, height * ratio
    threshold = ASPECT_THRESHOLD_PX
    if responsive:
        threshold = max(threshold, min(width / natural_width, height / natural_height))  # one file pixel, scaled up
    if target_height < target_width:
        return abs(target_height - height) < threshold
    return abs(target_width - width) < threshold


def check_aspect_ratio(page: ImagePage) -> tuple[bool, str]:
    wrong, count = [], 0
    for image in page.parser.images:
        attrs = image["attrs"]
        fallback = attrs.get("src", "").strip()
        width, height = number(attrs.get("width", "")), number(attrs.get("height", ""))
        pairs = [(width, height, [fallback] + srcset_urls(attrs.get("srcset", "")), False)]
        for source in image["sources"]:  # a <source> with a width or height is sized by its own two only, as in Chrome;
            urls = srcset_urls(source.get("srcset", ""))  # with just one, the other side follows the file's shape
            if "width" in source or "height" in source:
                pairs.append((number(source.get("width", "")), number(source.get("height", "")), urls, False))
            else:
                pairs.append((width, height, urls, True))
        for display_width, display_height, urls, borrowed in pairs:
            if not (display_width and display_height):
                continue
            for src in dict.fromkeys(url for url in urls if url):
                facts = page.file(src)
                if facts["error"] or facts["kind"] not in RASTER or not (facts["width"] and facts["height"]):
                    continue
                count += 1
                if shapes_match(display_width, display_height, facts["width"], facts["height"], responsive=src != fallback):
                    continue
                size = f"{shown(src)} is {facts['width']}x{facts['height']}"
                display_size = f"{display_width}x{display_height}"
                wrong.append(at(image, f"{size}, a different shape from the <img>'s {display_size}; give its <source> "
                                       "its own width and height" if borrowed else f"{size} but set to {display_size}"))
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


def modern_alternatives(page: ImagePage, image: dict) -> tuple[bool, set[str]]:
    """Whether a selectable <source> offers WebP or AVIF, and which JPEG/PNG files can still be chosen within such a
    source. An unconditional source blocks later sources. Viewport-specific media conditions remain unknown."""
    modern, mixed = False, set()
    for source in image["sources"]:
        source_type = source.get("type", "").partition(";")[0].strip().lower()
        if source_type and source_type not in BROWSER_TYPES:
            continue
        files = {url: page.file(url) for url in srcset_urls(source.get("srcset", ""))}
        if not files:
            continue
        if any(not facts["error"] and facts["kind"] in ("webp", "avif") for facts in files.values()):
            modern = True
            mixed.update(url for url, facts in files.items() if facts["kind"] in ("jpeg", "png"))
        if source.get("media", "").strip().lower() in ("", "all"):
            break
    return modern, mixed


def check_modern_format(page: ImagePage) -> tuple[bool, str]:
    heavy = []
    for image in page.parser.images:
        modern, mixed = modern_alternatives(page, image)
        for src in page.image_urls(image):
            facts = page.file(src)
            heavy_legacy = not facts["error"] and facts["kind"] in ("jpeg", "png") and facts["bytes"] >= MODERN_FORMAT_MIN_BYTES
            if heavy_legacy and (not modern or src in mixed):
                reason = "still selectable from a mixed-format srcset" if src in mixed else "with no WebP or AVIF version"
                detail = f"{shown(src)} is {facts['kind'].upper()}, {facts['bytes'] // 1000} KB, {reason}"
                heavy.append((facts["bytes"], at(image, detail)))
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
    return True, f"{len(page.json_ld)} JSON-LD images, all readable and meeting applicable size guidance" if page.json_ld else "no JSON-LD image"


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


def check_site(start: str, files: dict | None = None, limit: int = page_check.MAX_PAGES) -> bool:
    """Checks the images of every page found under the start address, up to the limit; one block per page and a total. True if any failed."""
    files = {} if files is None else files
    so_far = " so far in this run" if files else ""  # the cache is shared with the inputs before this one
    passed_pages = failed_pages = 0
    for url, source, page in page_check.site_pages(start, limit=limit):
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
    checked = passed_pages + failed_pages
    print(f"{start}: {checked} page{'s' * (checked != 1)} checked, {passed_pages} passed, {failed_pages} failed; {file_totals(files)}{so_far}.\n")
    return failed_pages > 0


if __name__ == "__main__":
    names, limit = page_check.page_limit(sys.argv[1:])
    if not names:
        sys.exit(__doc__.strip().splitlines()[-1])
    any_failed, shared_files = False, {}
    for name in names:
        if name.startswith(("http://", "https://")):
            any_failed |= check_site(name, shared_files, limit)
            continue
        path = Path(name).resolve()
        results = run_checks(path.read_text(encoding="utf-8", errors="replace"), path, shared_files)
        any_failed |= not all(passed for _, passed, _ in results)
        print(f"== {name}\n{report(results)}\n")
    if len(names) > 1 or not names[0].startswith(("http://", "https://")):  # a site prints its own total
        print(f"In all: {file_totals(shared_files)}.")
    sys.exit(1 if any_failed else 0)
