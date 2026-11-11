#!/usr/bin/env python3
"""Search the saved guides by meaning, with the local embedding model in LM Studio.

Build:  python3 vectors.py   (splits every saved page into sections at its headings, embeds each
        piece and writes vectors/pieces.json and vectors/values.f32; a full rebuild every time)
Search: search(query, guide_keys, count) from the MCP server.

The model is LM Studio's OpenAI-compatible endpoint on 127.0.0.1. When it or the vectors folder is
missing, search raises RuntimeError with the reason; keyword search does not depend on any of this.
Standard library only.
"""
import json
import math
import operator
import re
import sys
import time
import urllib.error
import urllib.request
from array import array

import sync_google_docs as sync

ENDPOINT = "http://127.0.0.1:1234/v1/embeddings"
MODEL = "text-embedding-qwen3-embedding-0.6b"
DIMENSIONS = 1024
BATCH_SIZE = 64
BUILD_TIMEOUT_SECONDS = 120
QUERY_TIMEOUT_SECONDS = 5
QUERY_INSTRUCTION = "Given a question about building or writing a web page, retrieve the section of Google's guidelines that answers it"
PIECE_CHARACTERS = 1200
VECTORS_FOLDER = sync.REPO_ROOT / "vectors"
PIECES_FILE = VECTORS_FOLDER / "pieces.json"
VALUES_FILE = VECTORS_FOLDER / "values.f32"

FENCE_LINE = re.compile(r"^\s*(`{3,}|~{3,})")
HEADING_LINE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
HEADING_ATTRIBUTES = re.compile(r"\s*\{:[^}]*\}$")  # Google's "{: #anchor }" suffix

dot = getattr(math, "sumprod", None) or (lambda a, b: sum(map(operator.mul, a, b)))


def headings(lines: list[str]) -> list[tuple[int, int, str]]:
    """(line index, level, text) for each Markdown heading outside code blocks."""
    found = []
    fence = None
    for index, line in enumerate(lines):
        fence_match = FENCE_LINE.match(line)
        if fence_match:
            marker = fence_match.group(1)
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        heading_match = None if fence else HEADING_LINE.match(line)
        if heading_match:
            text = HEADING_ATTRIBUTES.sub("", heading_match.group(2))
            found.append((index, len(heading_match.group(1)), text))
    return found


def piece_ranges(lines: list[str], start: int, end: int) -> list[tuple[int, int]]:
    """(first, last) line indexes of pieces of at most PIECE_CHARACTERS, cut at blank lines, else at line ends."""
    units, first = [], None  # runs of non-blank lines; a run over the cap becomes its lines
    for index in range(start, end + 1):
        if index < end and lines[index].strip():
            first = index if first is None else first
        elif first is not None:
            if len("\n".join(lines[first:index])) > PIECE_CHARACTERS:
                units.extend((line, line) for line in range(first, index))
            else:
                units.append((first, index - 1))
            first = None
    pieces: list[tuple[int, int]] = []
    for unit_first, unit_last in units:
        if pieces and len("\n".join(lines[pieces[-1][0]:unit_last + 1])) <= PIECE_CHARACTERS:
            pieces[-1] = (pieces[-1][0], unit_last)
        else:
            pieces.append((unit_first, unit_last))
    return pieces


def page_pieces(guide: sync.Guide, file_name: str, page: sync.GuidePage) -> list[tuple[dict, str]]:
    """(metadata, text to embed) for each piece of one saved page."""
    lines = (guide.folder / file_name).read_text(encoding="utf-8", errors="replace").splitlines()
    starts = [(0, page.title)] + [(index, text) for index, _, text in headings(lines) if index > 0]
    found = []
    for number, (start, heading) in enumerate(starts):
        end = starts[number + 1][0] if number + 1 < len(starts) else len(lines)
        for first, last in piece_ranges(lines, start, end):
            if first == last == start and number > 0:
                continue  # a heading with nothing under it before the next heading
            meta = {"guide": guide.key, "file": file_name, "title": page.title, "url": page.page_url,
                    "heading": heading, "first_line": first + 1, "last_line": last + 1}
            found.append((meta, f"{page.title} › {heading}\n" + "\n".join(lines[first:last + 1])))
    return found


def embed(texts: list[str], timeout: float) -> list[list[float]]:
    request = urllib.request.Request(
        ENDPOINT, data=json.dumps({"model": MODEL, "input": texts}).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.load(response)["data"]
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"LM Studio answered HTTP {error.code}") from None
    except (OSError, ValueError, KeyError, TypeError):
        raise RuntimeError("LM Studio did not answer at 127.0.0.1:1234") from None
    vectors = [item["embedding"] for item in sorted(data, key=lambda item: item.get("index", 0))]
    if len(vectors) != len(texts) or any(len(vector) != DIMENSIONS for vector in vectors):
        raise RuntimeError(f"LM Studio did not return one {DIMENSIONS}-value vector per text (is {MODEL} loaded?)")
    unit = []
    for vector in vectors:
        norm = math.sqrt(dot(vector, vector)) or 1.0
        unit.append([value / norm for value in vector])
    return unit


def build() -> int:
    """Embed every piece of every saved page and write the vectors folder; returns the piece count."""
    pieces = []
    for guide in sync.GUIDES.values():
        for page in sync.read_saved_pages(guide):
            pieces.extend(page_pieces(guide, guide.file_name(page.path), page))
    values = array("f")
    for start in range(0, len(pieces), BATCH_SIZE):
        for vector in embed([text for _, text in pieces[start:start + BATCH_SIZE]], BUILD_TIMEOUT_SECONDS):
            values.extend(vector)
    VECTORS_FOLDER.mkdir(exist_ok=True)
    VALUES_FILE.with_suffix(".tmp").write_bytes(values.tobytes())
    PIECES_FILE.with_suffix(".tmp").write_text(json.dumps({"model": MODEL, "pieces": [meta for meta, _ in pieces]}), encoding="utf-8")
    VALUES_FILE.with_suffix(".tmp").replace(VALUES_FILE)
    PIECES_FILE.with_suffix(".tmp").replace(PIECES_FILE)
    return len(pieces)


loaded: dict = {"mtime": None, "pieces": [], "vectors": []}


def load() -> tuple[list[dict], list]:
    try:
        mtime = PIECES_FILE.stat().st_mtime
        if mtime != loaded["mtime"]:
            pieces = json.loads(PIECES_FILE.read_text(encoding="utf-8"))["pieces"]
            values = array("f")
            values.frombytes(VALUES_FILE.read_bytes())
            if len(values) != len(pieces) * DIMENSIONS:
                raise RuntimeError("the vectors are being rebuilt; try again in a minute")
            vectors = [values[index * DIMENSIONS:(index + 1) * DIMENSIONS] for index in range(len(pieces))]
            loaded.update(mtime=mtime, pieces=pieces, vectors=vectors)
    except (OSError, ValueError, KeyError):
        raise RuntimeError("no vectors yet: run python3 vectors.py") from None
    return loaded["pieces"], loaded["vectors"]


def search(query: str, guide_keys: set[str], count: int = 5) -> list[tuple[float, dict]]:
    """The `count` pieces closest in meaning to `query`, best first, as (score, metadata)."""
    pieces, vectors = load()
    wanted = embed([f"Instruct: {QUERY_INSTRUCTION}\nQuery:{query}"], QUERY_TIMEOUT_SECONDS)[0]
    scored = [(dot(wanted, vector), meta) for meta, vector in zip(pieces, vectors) if meta["guide"] in guide_keys]
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[:count]


if __name__ == "__main__":
    began = time.monotonic()
    try:
        built = build()
    except RuntimeError as error:
        sys.exit(f"Could not build the vectors: {error}")
    print(f"Embedded {built} pieces in {time.monotonic() - began:.0f} s into {VECTORS_FOLDER.relative_to(sync.REPO_ROOT)}/")
