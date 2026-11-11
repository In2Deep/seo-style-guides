# seo-style-guides

Local copies of three Google developer guides, a script that keeps them current, and an MCP server
that lets an AI agent search and read them.

| Guide | Key | Source |
|---|---|---|
| Google developer documentation style guide | `style` | <https://developers.google.com/style> |
| Google Search Central SEO documentation | `seo` | <https://developers.google.com/search/docs> |
| Google crawling infrastructure documentation | `crawling` | <https://developers.google.com/crawling> |

Everything runs on Python 3.10 or later with the standard library only. There is nothing to install.

## Layout

| Path | What it holds |
|---|---|
| `sync_google_docs.py` | Downloads each guide page as Markdown and compares it with the saved copy by SHA-256. |
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

After `--save`, `git diff guides` shows exactly what Google changed.

The script fetches pages one at a time, each on a new connection, with a 0.25 second pause between
them. The 20-page `crawling` guide takes about 13 seconds; all three guides are about 250 pages.
Run one copy at a time: two runs at once slow each other down.

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

The server has six tools:

| Tool | What it does |
|---|---|
| `search_google_docs` | Finds a word or phrase in the saved pages. |
| `list_google_docs` | Lists a guide's pages by section. |
| `read_google_doc` | Returns one saved page, or one section of it, with its source URL. |
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
