# seo-style-guides: rules for people and agents

This repo is the `lx-seo` Claude Code plugin: saved copies of Google's SEO, crawling, style,
Lighthouse and web.dev guides, an MCP server that searches and quotes them, and checkers for
pages, images and JSON-LD. The README explains the layout and every tool. Brandon Hatch owns it
and decides. If a request conflicts with a rule here, say so in one line, then do what he decides.

## How we work

- Keep it simple. Build the smallest thing that works: Python standard library only, a few tests,
  no databases or extra services. Don't build for a feature that doesn't exist yet.
- A question ("what do you think?", "why does this fail?") means investigate and report, then ask
  before fixing, loading a model or starting a long job. Answer a yes or no question with yes or
  no first.
- Change only what was asked. If something else needs changing, list it and ask first.
- Report whether it works. Don't paste diffs unless asked.
- In chat, use plain words and spell out acronyms the first time.
- No em dashes anywhere you write: code comments, docs, commit messages or chat. No double hyphens
  as punctuation either (command flags like `--save` are fine). Use a colon, comma or full stop.

## Before every commit

1. `git pull --ff-only`. A GitHub Action commits updated guides every Monday at about 5 a.m.
   Pacific, so the remote moves without you.
2. Run the tests: `python3 -B -m unittest discover -s mcp-server`.
3. For any change a user would notice, raise the version in `.claude-plugin/plugin.json` (patch
   for fixes, minor for a new tool or skill). Claude Code updates an installed plugin only when
   the version changes. `CHANGES.md` is written by the sync script; don't edit it by hand.
4. Commit locally after every change, as Brandon Hatch with `In2Deep@users.noreply.github.com`
   (set in this repo's git config). Never use a personal email address.
5. Push to GitHub (`In2Deep/seo-style-guides`) only when Brandon asks.

## The guides

- `guides/` holds Google's pages word for word (CC BY 4.0) and the W3C accessibility vocabulary.
  Never edit them by hand. Update them only when asked, with
  `python3 -B sync_google_docs.py --guide <key> --save`, or let the weekly Action do it.
- Quote only what a page says, word for word, and cite its source URL. `check_google_quote`
  confirms a quote.
- When guides disagree, the tier rule in the README ("When guides disagree") decides.

## Search by meaning

- `vectors/` is not in git. `python3 vectors.py` rebuilds it in about 5 minutes with the
  embedding model in LM Studio at `127.0.0.1:1234`. Ask before rebuilding or loading the model.
- Load the model at a context of 7189:
  `lms load text-embedding-qwen3-embedding-0.6b --context-length 7189 -y`. At the maximum
  (32768) it fails to load, and below about 5,100 tokens the longest sections get cut off.

## This repo is public

- Nothing personal goes in files, commits, tests or examples: no email addresses, home folder
  paths, keys or tokens, and no names or details of clients, employers or other projects.
- Work for other projects stays out. Test pages and examples are made up or come from public
  sites.

## How it runs on Brandon's Mac

- Claude Code installs the plugin straight from this folder (local marketplace
  `seo-style-guides`), so a change here reaches a Claude session once it restarts. Codex runs the
  same server through `mcp-server/launch.sh`.
- `launch.sh` finds Python 3.10 or newer on its own, because the apps give MCP servers a bare
  PATH where `/usr/bin/python3` is too old.
