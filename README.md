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
| `skills/json-ld/` | The `json-ld` skill: check a whole site's JSON-LD and report. |
| `.claude-plugin/` | The plugin and marketplace manifests that let Claude Code install this repo as a plugin. |

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

Pages are saved byte for byte, so the standard tool also verifies a copy:

```bash
cd guides/seo && shasum -a 256 -c SHA256SUMS
```

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

```bash
python3 page_check.py https://example.com/
```

Given a web address, it checks every page of that site under that address. It finds the pages from
the site's sitemap and by following links on the same site, and prints one PASS or FAIL line per
page with only the failed checks. For a fetched page, the noindex check also reads the
`X-Robots-Tag` HTTP header. It stops at 500 pages, and a site behind a login cannot be checked.

## Search by meaning (optional)

The tool works without this. With no setup, `search_google_docs` is a keyword search, and every
other tool works the same. Search by meaning adds the five closest sections under the keyword
results, so a question finds the right section even when it uses different words.

It needs a local embedding model. The defaults are LM Studio's local server on `127.0.0.1:1234`
with the `text-embedding-qwen3-embedding-0.6b` model loaded.

```bash
python3 vectors.py   # several minutes; writes the vectors/ folder
```

The `vectors/` folder is the switch:

- **No folder:** keyword search only. Nothing else to do.
- **Folder exists:** search by meaning is on. If the embedding server is not running, search says
  so and stays keyword only. An update through the MCP server rebuilds the vectors itself; after
  an update from the command line, run `python3 vectors.py` again.
- **To turn it off:** delete the `vectors/` folder.

### Use a different embedding server

The settings are three lines at the top of `vectors.py`:

| Line | What it is | Default |
|---|---|---|
| `ENDPOINT` | The embedding server's address. Any server with an OpenAI-compatible `/v1/embeddings` works. | `http://127.0.0.1:1234/v1/embeddings` |
| `MODEL` | The model's name as that server knows it. | `text-embedding-qwen3-embedding-0.6b` |
| `DIMENSIONS` | How many numbers the model returns per text. | `1024` |

After changing any of them, delete `vectors/` and run `python3 vectors.py` again, because vectors
from one model cannot be searched with another. `QUERY_INSTRUCTION` and the `Instruct: ... Query:`
wrapper in `search()` are written for Qwen3 embedding models; another model may want a different
query format. If you change these lines, a later `git pull` may ask you to merge them.

## Set it up in Claude Code

There are two ways. Both give a session the same ten tools.

### As a plugin

From a copy of this repo on your computer:

```
/plugin marketplace add /path/to/seo-style-guides
/plugin install seo-style-guides@seo-style-guides
```

From GitHub, replace `<owner>/<repo>` with the repository that holds it:

```
/plugin install seo-style-guides --marketplace <owner>/<repo>
```

A plugin install is a snapshot. It gives you keyword search, every checker, and the `json-ld`
skill with no setup. Claude Code replaces the plugin's folder when the plugin updates, so guide
updates and vectors made inside it do not last. To keep your own updates or use search by meaning,
use a clone.

### As a clone

Clone the repo, then add this to a project's `.mcp.json`, with the full path to where you put it:

```json
{
  "mcpServers": {
    "google_seo_and_style_guides": {
      "command": "/path/to/seo-style-guides/mcp-server/launch.sh",
      "args": []
    }
  }
}
```

Start a new session after either one. Sessions that were already open don't pick it up.

## What to ask for

You don't call the tools yourself. Ask in plain words and the session picks the tool.

| You want | Ask something like | What runs |
|---|---|---|
| Google's rule on a topic | "What does Google say about image alt text?" | `search_google_docs`, then `read_google_doc` |
| Proof a quote is real | "Confirm that quote is in Google's page." | `check_google_quote` |
| A JSON-LD block checked | "Check this JSON-LD against Google's requirements." | `check_structured_data` |
| One built page checked | "Run the page check on dist/index.html." | `check_page` |
| A whole site's JSON-LD checked | `/seo-style-guides:json-ld https://example.com` | the `json-ld` skill and `page_check.py` |
| To know if Google changed anything | "Are the saved guides current?" | `check_google_docs` |
| What changed, and when | "What changed in the guides since 2026-11-01?" | `google_docs_changes` |
| The newest guides | "Update the SEO guide." | `update_google_docs` |

The `json-ld` skill checks every page under the address: required and recommended properties,
markup that doesn't match what the page shows, and pages that fit a Google search feature but have
no markup. It reports and changes nothing. It reads JSON-LD only, not microdata or RDFa.

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

## Credits

The pages in `guides/` are unchanged copies of documentation published by Google LLC on
developers.google.com, web.dev and developer.chrome.com. Google licenses that content under the
[Creative Commons Attribution 4.0 License](https://creativecommons.org/licenses/by/4.0/) and its
code samples under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0). Each
saved page's source address is listed in its guide's `README.md`.

The code in this repo is under the MIT License; see `LICENSE`. That license does not cover the
pages in `guides/`.

This project is not affiliated with or endorsed by Google.
