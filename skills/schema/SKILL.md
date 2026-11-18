---
name: schema
description: Find structured data a website could add. For every page, names the Google search features its visible content fits but its markup doesn't cover, and drafts the JSON-LD from what the page already shows. Use when asked for schema or structured data improvements, opportunities, or what markup to add, for a whole site, a local preview, or one page. It reports and drafts only; it doesn't edit the site. With the word accessibility, or when asked for accessibility or disability metadata, it also drafts schema.org accessibility properties (accessibilityFeature, accessMode, accessibilityHazard), which Google Search doesn't use.
argument-hint: <address> [accessibility]
---

# Schema improvements

The argument is the address to review, for example `https://example.com` or `http://127.0.0.1:4321/`. The review covers every page under that address. Without an argument, ask which address.

Add the word `accessibility` after the address, or ask for accessibility metadata, to also run [Accessibility metadata](#accessibility-metadata) after the steps.

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

## Accessibility metadata

Run this only when it was asked for. It drafts schema.org's accessibility properties, such as `accessibilityFeature` and `accessMode`. These describe how people with disabilities can use the content.

Google Search doesn't use these properties. They are the one exception to step 2, and they help other tools, not search results. Keep them apart from the Google suggestions everywhere in the report.

1. Search the guides for `accessibilityFeature` and `accessMode` with `search_google_docs`. If a Google guide documents them now, follow that guide: Google Search's rules come first. If none does, say so in the report.

2. Read `accessibility-vocabulary.md` next to this file. It lists the allowed values, which types take them, and when each value is true of a web page. Use only those values. For a value's full definition, read the W3C report itself: `read_google_doc` with page `a11y-vocab/index.md`. Confirm every W3C quote in the report with `check_google_quote` on that page.

3. For each page whose main content is a `CreativeWork`, read the HTML. Decide which values are true. Look at the images and their `alt` text, the headings, any `<video>`, `<audio>` and `<track>` elements, transcripts, `role` attributes, and `<math>`. The page checker's image alt check helps with `alternativeText`.
   - Draft only values the page proves.
   - A value the HTML can't prove goes under "needs a true value from the owner". This covers hazards, `readingOrder`, `displayTransformability` and contrast.
   - Never draft `none` or `unknown`, and never write an `accessibilitySummary` claim the site doesn't make.

4. Add the properties to the page's main item, in the draft from step 4 or in its existing markup. Run `check_structured_data` on the whole result to confirm the item still has Google's required properties.

5. If a page already has accessibility properties, flag values that aren't in the vocabulary, are deprecated, contradict each other (for example `none` with another value), or aren't true of the page.

## Report

Per page: address, current types, each suggested feature with the Google page that documents it, the draft JSON-LD, and the true values still needed. End with the suggestions in priority order, most useful first, and say why.

If accessibility metadata ran, add a separate section after the priority list. Head it "Accessibility metadata (not used by Google Search)". Per page, list the drafted properties, the evidence on the page for each value, the values that need the owner, and any problems with existing values. Cite the W3C vocabulary, not a Google page. Don't rank these suggestions with the Google suggestions.
