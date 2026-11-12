---
name: schema
description: Find structured data a website could add. For every page, names the Google search features its visible content fits but its markup doesn't cover, and drafts the JSON-LD from what the page already shows. Use when asked for schema or structured data improvements, opportunities, or what markup to add, for a whole site, a local preview, or one page. It reports and drafts only; it doesn't edit the site.
argument-hint: <address>
---

# Schema improvements

The argument is the address to review, for example `https://example.com` or `http://127.0.0.1:4321/`. The review covers every page under that address. Without an argument, ask which address.

This skill reports and drafts. Don't change the site's files unless the user then asks. For mistakes in markup a page already has, the `json-ld` skill in this plugin does that.

A site behind a login can't be reviewed. Don't enter a password; ask for the address of a local preview of the same build instead.

## Steps

1. Run the page checker on the address to get the page list and each page's current JSON-LD types:

   ```sh
   python3 -B "${CLAUDE_PLUGIN_ROOT}/page_check.py" <address>
   ```

   If this skill is not running from an installed plugin, `page_check.py` is at the root of the seo-style-guides repository.

2. Read `appearance--structured-data--search-gallery` with `read_google_doc`. It lists the search features Google supports. Don't suggest a type Google documents no search feature for.

3. For each page, fetch the HTML and read what a visitor sees. Decide which features the page's content fits and doesn't already mark up. For each one, read Google's page for that feature, including who is eligible and its content rules. Say so when a feature is limited to certain kinds of sites.

4. Draft the JSON-LD for each suggestion.
   - Use only values that are visible on the page. Never invent a value.
   - Where a required value isn't on the page, leave it out of the draft and list it as "needs a true value".
   - Run `check_structured_data` on each draft and report what it still lacks.

5. For markup a page already has, list recommended properties it could add where the page shows a true value for them.

6. Confirm every Google quote in the report with `check_google_quote`.

## Report

Per page: address, current types, each suggested feature with the Google page that documents it, the draft JSON-LD, and the true values still needed. End with the suggestions in priority order, most useful first, and say why.
