# seo-style-guides

Local copies of seven Google developer guides, a script that keeps them current, a page checker,
and an MCP server that lets an AI agent search and read them.

| Guide | Key | Source |
|---|---|---|
| Google developer documentation style guide | `style` | <https://developers.google.com/style> |
| Google Search Central SEO documentation | `seo` | <https://developers.google.com/search/docs> |
| Google crawling infrastructure documentation | `crawling` | <https://developers.google.com/crawling> |
| Lighthouse documentation and audits | `lighthouse` | <https://developer.chrome.com/docs/lighthouse/overview> |
| web.dev Core Web Vitals articles | `vitals` | <https://web.dev/articles/vitals> |
| web.dev Learn courses: performance, images, accessibility, HTML, forms and responsive design | `learn` | <https://web.dev/learn> |
| Google Search help and documentation updates | `search-help` | <https://developers.google.com/search/help> |

Everything runs on Python 3.10 or later with the standard library only. There is nothing to install.

## Layout

| Path | What it holds |
|---|---|
| `sync_google_docs.py` | Downloads each guide page as Markdown and compares it with the saved copy by SHA-256. |
| `structured_data.py` | Checks a page's JSON-LD against the required and recommended property tables in the saved structured-data pages. |
| `page_check.py` | Checks a built HTML page before it is deployed. Each check quotes the Google page it comes from. |
| `CHANGES.md` | One dated entry per guide each time `--save` changes it, naming the pages changed, added or removed. |
| `vectors.py` | Splits the saved pages into sections and embeds them with a local model, for search by meaning. |
| `vectors/` | The section vectors `vectors.py` writes (about 32 MB). Not in git; rebuild with `python3 vectors.py`. |
| `guides/<key>/` | The saved pages, a `SHA256SUMS` file, and a generated `README.md` that lists every page. |
| `mcp-server/server.py` | The MCP server (stdio). It serves the saved copies and can run the sync as a background job. |
| `mcp-server/launch.sh` | Starts the server with the first Python 3.10 or later on the machine. |
| `mcp-server/test_server.py` | Tests that drive the server through its launcher. |

## Check and update the copies

```bash
python3 sync_google_docs.py                     # check every guide; write nothing
python3 sync_google_docs.py --guide seo         # check one guide
python3 sync_google_docs.py --guide seo --save  # update its pages, SHA256SUMS and README.md
```

Exit status: `0` every copy checked is current (or `--save` updated it), `1` a copy is out of
date, `2` a guide could not be fetched.

After `--save`, `git diff guides` shows exactly what Google changed, and `CHANGES.md` gets an entry.

The script fetches eight pages at a time. A check of all seven guides (about 500 pages) takes about 45 seconds. Only one run can go at a time: a second run started while one is going is refused.

## Check a page before it is deployed

```bash
python3 page_check.py site/dist/index.html site/dist/fire.html
```

The checker reads each built HTML file and prints PASS or FAIL for 14 checks: title, meta
description, viewport, `html lang`, doctype, charset, noindex, one canonical link, an absolute
canonical link, image alt, link href, link text, generic link text, and JSON-LD required
properties. A failure shows the tag and its line. Each check prints the exact Google quote it rests
on and the page's source URL. Missing recommended JSON-LD properties are listed as a notice.

Exit status: `0` every check passed in every file, `1` a check failed. It fetches nothing and runs
no JavaScript, so it checks the HTML as built, not as a browser renders it.

## Search by meaning

```bash
python3 vectors.py   # several minutes; run it after an update changes pages
```

`vectors.py` needs LM Studio's local server on `127.0.0.1:1234` with the
`text-embedding-qwen3-embedding-0.6b` model loaded. With the vectors built, `search_google_docs`
adds the five closest sections by meaning under its keyword results. Without them, or with
LM Studio off, search is keyword only and says so. An update through the MCP server rebuilds the
vectors itself.

Pages are saved byte for byte, so the standard tool also verifies a copy:

```bash
cd guides/seo && shasum -a 256 -c SHA256SUMS
```

## Use the MCP server

Register the launcher with an MCP client. For Claude Code, add this to a project's `.mcp.json`:

```json
{
  "mcpServers": {
    "google_seo_and_style_guides": {
      "command": "/Users/brandon/seo-style-guides/mcp-server/launch.sh",
      "args": []
    }
  }
}
```

The server has ten tools:

| Tool | What it does |
|---|---|
| `search_google_docs` | Finds a word or phrase in the saved pages, plus the closest sections by meaning. |
| `list_google_docs` | Lists a guide's pages by section. |
| `read_google_doc` | Returns one saved page, or one section of it, with its source URL. |
| `check_google_quote` | Says whether a quote appears word for word in a saved page, and where. |
| `check_structured_data` | Checks JSON-LD against Google's required and recommended property tables. |
| `check_page` | Runs the page checker on HTML text or a local HTML file. |
| `google_docs_changes` | Lists the `CHANGES.md` entries, newest first, since a date or the latest 10. |
| `check_google_docs` | Compares the saved copies with Google's live guides. Writes nothing. |
| `update_google_docs` | Saves Google's current version of one guide over its local copy. |
| `google_docs_job` | Reports the progress and result of a check or update. |

## Test

```bash
python3 -B -m unittest discover -s mcp-server
```

The tests run offline against the saved copies. One more test checks the `crawling` guide against
Google; it runs only when `GOOGLE_DOCS_NETWORK_TESTS` is set:

```bash
GOOGLE_DOCS_NETWORK_TESTS=1 python3 -B -m unittest discover -s mcp-server
```
