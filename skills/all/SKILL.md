---
name: all
description: Run every check in this plugin on a website and write one report. Asks its questions once at the start, runs the page, image and Google-Agent checkers one after another, then does the reading that the json-ld, schema, images and google-agent skills do. That covers markup that doesn't match the page, structured data the pages could add (drafted), pictures beside their alt text, the first big picture at phone and desktop width, and Google's six Google-Agent questions. Use when asked to run all the checks, a full or complete check, or an audit of everything this plugin checks. For one kind of problem, the skill for it is quicker. It reports only; fixing is a separate request.
argument-hint: <address> [only] [accessibility] [blocklist file or address ...]
---

# All checks

This skill runs this plugin's `json-ld`, `schema`, `images` and `google-agent` skills on one site and writes one report. Read their files first. They are next to this one:

- `${CLAUDE_PLUGIN_ROOT}/skills/json-ld/SKILL.md`
- `${CLAUDE_PLUGIN_ROOT}/skills/schema/SKILL.md`, and `accessibility-vocabulary.md` beside it when accessibility metadata is wanted
- `${CLAUDE_PLUGIN_ROOT}/skills/images/SKILL.md`
- `${CLAUDE_PLUGIN_ROOT}/skills/google-agent/SKILL.md`

If this skill is not running from an installed plugin, they are in `skills/` at the root of the seo-style-guides repository. Follow their steps and rules, including where their tools come from and what to do when the tool server didn't start, except where this file says otherwise.

This skill reports. Don't change the site's files or any firewall, CDN or server setting unless the user then asks for fixes.

## Before you start

The argument is the site's address, for example `https://example.com` or `http://127.0.0.1:4321/`. The checks cover that page and every page whose address starts with it, so `https://example.com/blog/` also covers `https://example.com/blog/first-post/`. After the address, the word `only` checks just the page at that address, the word `accessibility` asks for accessibility metadata, and anything else is a blocklist for the Google-Agent check.

Ask what you need in one message, before running anything, and only what the arguments didn't answer:

1. Which address, if there is none. A built HTML file isn't enough, because the Google-Agent check needs a running site; ask for the address of a local preview instead. A site behind a login can't be checked; don't enter a password.
2. Whether the user runs or manages the site. The Google-Agent check sends Google-Agent's name, so on anyone else's site skip it and say so under Not tested.
3. The site's blocklists, as step 1 of the `google-agent` skill describes: lists only, never keys or passwords.
4. Whether to add accessibility metadata to the schema suggestions.

After that, don't stop for answers again until step 5.

## Steps

1. Read each Google page the four skills say to read, once, with `read_google_doc`.

2. Run the three checkers one after another, in this order, never at the same time. Add `--blocklist "<list>"` for each blocklist, or leave it out if there are none. With `only`, add `--pages 1` to all three, so each stops after the page given:

   ```sh
   python3 -B "${CLAUDE_PLUGIN_ROOT}/page_check.py" "https://example.com/"
   python3 -B "${CLAUDE_PLUGIN_ROOT}/image_check.py" "https://example.com/"
   python3 -B "${CLAUDE_PLUGIN_ROOT}/agent_check.py" "https://example.com/" --blocklist "blocked.txt"
   ```

   Three crawlers at once can trip a site's rate limit or ban rule. The Google-Agent checker goes last, because a rule that bans its name could turn away any check after it. The page checker's output serves both the `json-ld` and `schema` skills, so it runs once. Each checker exits with status 1 when it finds a failure; that is a result, not a crash. If a checker reports pages that got no answer, stop and tell the user: their own address may be banned there, and nothing more can be learned until the ban is lifted.

3. Read the pages. Fetch each page's HTML once and use it for all of these:
   - `json-ld` steps 2 and 3: the markup beside the visible text, and each type's Google page.
   - `schema` steps 3 to 5: the features each page fits, the drafts, and recommended properties to add. Run its Accessibility metadata section only if it was asked for.
   - `images` step 3: the main pictures beside their alt text, and content pictures set as CSS backgrounds.

4. Measure the first big picture as `images` step 2 describes, at phone width (375) and desktop width (1440). If no browser is available, list it under Not tested.

5. Ask the six questions from `google-agent` step 3 in one message. Skip this step if the Google-Agent check was skipped.

6. Confirm every Google quote in the report with `check_google_quote`, and every W3C quote on page `a11y-vocab/index.md`.

## Report

Start with one line per checker: how many pages it checked (and image files, for the image checker) and how many failed. Then:

1. Fix first: every failure from every check, one line each with the page or file, what's wrong and the Google quote, in this order:
   - Turned away: the first section of the `google-agent` report.
   - Structured data: missing required properties and markup that doesn't match the page, from the `json-ld` report.
   - Images: the failures from the `images` report and its list of files to fix, heaviest first.
2. Could add: the `schema` suggestions in priority order, with their drafts and the true values still needed. Then the missing recommended properties from the `json-ld` report that have a true value.
3. Accessibility metadata (not used by Google Search), if it ran, as the `schema` report describes. Don't rank it with anything else.
4. To confirm: every notice the checkers printed, the values only the owner can give, and the six Google-Agent checks with the user's answers, or "not answered".
5. Not tested: what the `google-agent` report lists, plus every check or step this run skipped and why.

A section with nothing in it gets one line that says so.
