# seo-style-guides

Local copies of seven Google developer guides and one W3C vocabulary, a script that keeps them current, a page checker,
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
| W3C Schema.org Accessibility Properties for Discoverability Vocabulary (not Google's) | `a11y-vocab` | <https://www.w3.org/2021/a11y-discov-vocab/latest/> |

Everything runs on Python 3.10 or later with the standard library only. There is nothing to install.

## Layout

| Path | What it holds |
|---|---|
| `sync_google_docs.py` | Downloads each guide page as Markdown and compares it with the saved copy by SHA-256. In the `crawling` guide, a page Google offers no Markdown for is converted from its HTML. |
| `structured_data.py` | Checks a page's JSON-LD against the required and recommended property tables in the saved structured-data pages. |
| `page_check.py` | Checks a built HTML page before it is deployed. Each check quotes the Google page it comes from. |
| `image_check.py` | Checks a page's images and opens their files: size, shape, format, names, alt text, lazy loading, favicon. Each check quotes the Google page it comes from. |
| `agent_check.py` | Checks whether Google-Agent gets into a site: each page loaded with and without Google-Agent's name, forms and CAPTCHA widgets, robots.txt, and blocklists against Google's addresses. Each check quotes the Google page it comes from. |
| `CHANGES.md` | One dated entry per guide each time `--save` changes it, naming the pages changed, added or removed. |
| `vectors.py` | Splits the saved pages into sections and embeds them with a local model, for search by meaning. |
| `vectors/` | The section vectors `vectors.py` writes (about 32 MB). Not in git; rebuild with `python3 vectors.py`. |
| `guides/<key>/` | The saved pages, a `SHA256SUMS` file, and a generated `README.md` that lists every page. |
| `mcp-server/server.py` | The MCP server (stdio). It serves the saved copies and can run the sync as a background job. |
| `mcp-server/launch.sh` | Starts the server with the first Python 3.10 or later on the machine. |
| `mcp-server/test_server.py` | Tests that drive the server through its launcher. |
| `skills/json-ld/` | The `/lx-seo:json-ld` action: find mistakes in a whole site's JSON-LD. |
| `skills/images/` | The `/lx-seo:images` action: find image problems on a whole site. |
| `skills/google-agent/` | The `/lx-seo:google-agent` action: check whether Google-Agent gets into a site, then ask what the checker can't see. |
| `skills/schema/` | The `/lx-seo:schema` action: find markup a site could add, and draft it. `accessibility-vocabulary.md` holds the allowed values for its optional accessibility metadata. |
| `.claude-plugin/` | The plugin and marketplace manifests. The plugin is named `lx-seo`, so its actions are typed `/lx-seo:<action>`. |

## Check and update the copies

```bash
python3 sync_google_docs.py                     # check every guide; write nothing
python3 sync_google_docs.py --guide seo         # check one guide
python3 sync_google_docs.py --guide seo --save  # update its pages, SHA256SUMS and README.md
```

Exit status: `0` every copy checked is current (or `--save` updated it), `1` a copy is out of
date, `2` a guide could not be fetched.

After `--save`, `git diff guides` shows exactly what Google changed, and `CHANGES.md` gets an entry.

A GitHub Action (`.github/workflows/update-guides.yml`) does this every Monday: it saves all the
guides, runs the tests, and commits any changes with the plugin's version raised, so installed
copies update. It commits nothing if more than 10 saved pages would be deleted, since that
usually means Google blocked the download. A clone gets the updates with `git pull`; if it uses
search by meaning, rebuild the vectors after pulling with `python3 vectors.py`.

The script fetches eight pages at a time. A check of all eight guides (about 500 pages) takes about 45 seconds. Only one run can go at a time: a second run started while one is going is refused.

Google's pages are saved byte for byte, so the standard tool also verifies a copy:

```bash
cd guides/seo && shasum -a 256 -c SHA256SUMS
```

The `a11y-vocab` guide works differently. The W3C publishes the vocabulary as one HTML page with
no Markdown version, so the script finds the latest dated report, converts its HTML to Markdown,
and saves it as `guides/a11y-vocab/index.md`. Its first line names the dated report. Its
SHA-256 covers the converted text, so a new W3C version still shows up as a change, but the file
is not byte for byte what the W3C serves.

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

## Check a page's images

```bash
python3 image_check.py site/dist/index.html
python3 image_check.py https://example.com/
```

The image checker prints PASS or FAIL for 10 checks, each with the Google quote it rests on: width
and height on every `<img>`, a format Google Images supports (and a file extension that matches
it, and a fallback `src` on every `<img>`), descriptive file names (a build tool's hash is ignored),
alt text present and not a file name, the first picture of the main content not lazy loaded, every
file's shape matching its width and height (Lighthouse's rule, with subpixel rounding allowed on
smaller `srcset` candidates), and single-size files no more than twice as wide as they show. It
flags JPEG or PNG of 10 KB or more without a reachable WebP or AVIF source, including heavy
JPEG or PNG candidates that are still selectable in a mixed-format `srcset`. A viewport-specific
source can count as an alternative. The checker checks JSON-LD images, including standalone
`ImageObject` entries, and applies the 50,000-pixel recommendation where the guides give it,
including Article, Event, ProfilePage, Product, Recipe, and restaurant carousel markup. It also
checks for a square favicon in a format Google lists. It reads up to 30 MB per image, checks
headers and container boundaries, and reports unreadable or structurally incomplete files
(PNG, JPEG, GIF, BMP, WebP, AVIF, HEIC, TIFF, ICO, PPM, SVG). For a local file, image paths are
read from disk, following `<base href>`. A path that
starts with `/` is looked up in the nearest folder above the page that has it. Given a web address,
it checks every page the way `page_check.py` does and fetches each image once. It reads HTML only,
not CSS, lists every problem it finds, and changes nothing. Needs Python 3.10 or newer.

## Check whether Google-Agent gets in

```bash
python3 agent_check.py https://example.com/
python3 agent_check.py https://example.com/ --blocklist blocked.txt --blocklist https://www.spamhaus.org/drop/drop_v4.json
```

Google-Agent is the name Google's AI agents use when they visit a site because a person asked them
to. It doesn't follow robots.txt, so only a firewall, CDN, bot service or server rule can keep it
out. The checker loads every page (the first 50, or `--pages N`) twice: with Google-Agent's
published User-Agent string, read from the saved `crawling` guide, and with the same browser string
without Google-Agent in it. A page fails when the name alone changes the answer: blocked, rate
limited, a challenge page, or sent somewhere else. It also lists every form and where it sends,
in-page CAPTCHA widgets, and robots.txt lines that name Google-Agent. Each `--blocklist` (a file or
an address, in any common format) is compared with Google's current list of Google-Agent addresses,
`user-triggered-agents.json`, and every entry that covers one of them fails.

Its requests come from your computer, not from Google's addresses, and carry no Web Bot Auth
signature, so rules that trust Google's addresses or signatures aren't tested; the
`/lx-seo:google-agent` skill asks about those. It sends Google-Agent's name, so run it on sites you
run. It never submits a form and changes nothing.

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
/plugin install lx-seo@seo-style-guides
```

From GitHub:

```
/plugin marketplace add In2Deep/seo-style-guides
/plugin install lx-seo@seo-style-guides
```

Then restart Claude Code, so it starts the plugin's tool server. The server needs Python 3.10 or
newer; `mcp-server/launch.sh` finds one from Homebrew, python.org, pyenv, asdf, mise, conda or uv,
even when Claude starts it without your shell's PATH.

A plugin install is a snapshot. It gives you keyword search, every checker, and the `/lx-seo`
actions with no setup. Claude Code replaces the plugin's folder when the plugin updates, so guide
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
| Mistakes in a whole site's JSON-LD | `/lx-seo:json-ld https://example.com` | the `json-ld` skill and `page_check.py` |
| Image problems on a whole site | `/lx-seo:images https://example.com` | the `images` skill and `image_check.py` |
| Whether Google-Agent gets into a site | `/lx-seo:google-agent https://example.com` | the `google-agent` skill and `agent_check.py` |
| Markup a whole site could add | `/lx-seo:schema https://example.com` | the `schema` skill and `page_check.py` |
| The same, plus accessibility metadata | `/lx-seo:schema https://example.com accessibility` | the `schema` skill and the W3C accessibility vocabulary |
| To know if Google changed anything | "Are the saved guides current?" | `check_google_docs` |
| What changed, and when | "What changed in the guides since 2026-11-01?" | `google_docs_changes` |
| The newest guides | "Update the SEO guide." | `update_google_docs` |

`/lx-seo:json-ld` checks the markup every page already has: required and recommended properties,
and markup that doesn't match what the page shows. `/lx-seo:schema` looks for what each page could
add: Google search features the page fits, with the JSON-LD drafted from what the page shows.
Both report and change nothing. Both read JSON-LD only, not microdata or RDFa.

With `accessibility` after the address, `/lx-seo:schema` also drafts schema.org's accessibility
properties, such as `accessibilityFeature`, `accessMode` and `accessibilityHazard`. They describe
how people with disabilities can use a page's content, using the values in the W3C
[Schema.org Accessibility Properties for Discoverability Vocabulary](https://www.w3.org/2021/a11y-discov-vocab/latest/).
Google Search doesn't use these properties, so the report lists them in a separate section and
never ranks them with the Google suggestions. Values the HTML can't prove, such as hazards and
contrast, are listed for the site owner to confirm.

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

## When guides disagree

Seven of the guides are Google's. They come from different teams and sometimes disagree. For
example, a web.dev course suggests a title length, and the Search Central guide says there is no
limit. Google Search's own rules win:

| Tier | Guides | What they are |
|---|---|---|
| 1 | `seo`, `crawling`, `search-help` | Google Search's own rules for how it crawls, indexes and shows pages |
| 2 | `lighthouse` | Chrome's Lighthouse audits |
| 3 | `vitals`, `learn` | web.dev guidance |
| none | `style` | How to write documentation; it does not compete with the others |
| none | `a11y-vocab` | The W3C's values for schema.org accessibility properties, which Google Search doesn't use; it never overrides a Google guide |

The lower tier number wins, and a higher-numbered tier still applies wherever tier 1 is silent.
Every search result, page and guide listing shows its tier, and the server tells each session this
rule when it connects. The order is `GUIDE_TIERS` in `mcp-server/server.py`.

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

The Google pages in `guides/` are unchanged copies of documentation published by Google LLC on
developers.google.com, web.dev and developer.chrome.com. Google licenses that content under the
[Creative Commons Attribution 4.0 License](https://creativecommons.org/licenses/by/4.0/) and its
code samples under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0). Each
saved page's source address is listed in its guide's `README.md`.

Portions of this repository are reproduced from work created and shared by Google and used
according to terms described in the
[Creative Commons 4.0 Attribution License](https://creativecommons.org/licenses/by/4.0/).

The license below covers the code in this repo, not the pages in `guides/`.

The copy in `guides/a11y-vocab/` is the Schema.org Accessibility Properties for Discoverability
Vocabulary, copyright its contributors, published by the W3C Accessibility Discoverability
Vocabulary for Schema.org Community Group under the
[W3C Community Final Specification Agreement](https://www.w3.org/community/about/agreements/fsa/).
It is converted from HTML to Markdown, and its source address is listed in `guides/a11y-vocab/README.md`.

This project is not affiliated with or endorsed by Google or the W3C.

## License

MIT No Attribution (MIT-0), by Brandon Hatch. Do anything you like with it: use it, change it, sell it. You don't have to credit me. If you build something with it, a mention is appreciated, and no hard feelings if not.
