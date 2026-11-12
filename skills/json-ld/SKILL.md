---
name: json-ld
description: Check the JSON-LD structured data on every page of a website against Google's structured data guides, and report what is missing, wrong, or not true to the page. Use when asked to check or review JSON-LD, schema markup, or structured data for a whole site, a local preview, or one page. It reports only; fixing is a separate request.
argument-hint: <address>
---

# JSON-LD check

The argument is the address to check, for example `https://example.com` or `http://127.0.0.1:4321/`. The check covers every page under that address. Without an argument, ask which address.

This skill reports. Don't change the site's files unless the user then asks for fixes.

A site behind a login can't be checked. Don't enter a password; ask for the address of a local preview of the same build instead.

## Steps

1. Run the page checker on the address:

   ```sh
   python3 -B "${CLAUDE_PLUGIN_ROOT}/page_check.py" <address>
   ```

   If this skill is not running from an installed plugin, `page_check.py` is at the root of the seo-style-guides repository. The checker finds the pages from the sitemap and by following links. For each page it prints the JSON-LD types, the failures, and the missing recommended properties. It reads JSON-LD only, not microdata or RDFa. Say how many pages it checked.

2. For each page, fetch the HTML and read the JSON-LD beside the visible text. Google's structured data policies say markup must describe content a visitor can see. Read `appearance--structured-data--sd-policies` with `read_google_doc`, then flag every marked-up value that isn't on the page or isn't true.

3. For each type a page uses, read Google's page for that type with `search_google_docs` and `read_google_doc`, and use `check_structured_data` for the detail.
   - A missing required property is a failure.
   - A missing recommended property is a to-do, unless the site has no true value for it. Never invent a value.

4. For each page with no markup, or with only `Organization`, read `appearance--structured-data--search-gallery` and name any Google feature the page's visible content fits, with the Google page that documents it. Don't suggest a type Google documents no search feature for.

5. Confirm every Google quote in the report with `check_google_quote`.

## Report

One row per page: address, types found, failures, missing recommended properties (with whether a true value exists), markup that doesn't match the page, and suggested markup. Then the totals. List any other failures the checker printed, one line each, after the table.
