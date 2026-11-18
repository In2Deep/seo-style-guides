---
name: images
description: Find image problems on a website against Google's guides. Checks every page for missing width and height, a wrong shape, files much bigger than they show, JPEG or PNG with no WebP or AVIF version, formats Google Images can't use (such as HEIC), camera or generic file names, alt text that is a file name, a lazy loaded first picture, small structured data images and a favicon Google can't use. Use when asked to check, review or audit a site's images or pictures, for a whole site, a local preview, or one built HTML file. It reports only; converting, resizing or renaming images is a separate request.
argument-hint: <address or HTML file>
---

# Image check

The argument is the address to check, for example `https://example.com` or `http://127.0.0.1:4321/`, or a built HTML file such as `dist/index.html`. An address covers every page under it. Without an argument, ask which address.

This skill reports. Don't change, convert, resize or rename any file unless the user then asks for fixes.

A site behind a login can't be checked. Don't enter a password; ask for the address of a local preview of the same build instead.

## Steps

1. Run the image checker:

   ```sh
   python3 -B "${CLAUDE_PLUGIN_ROOT}/image_check.py" <address or file>
   ```

   If this skill is not running from an installed plugin, `image_check.py` is at the root of the seo-style-guides repository. It runs 10 checks on every page, each with the Google quote it rests on, and opens every image file to read its type and pixel size. It reads the HTML only, not CSS, so a size or shape set in CSS is not seen. Say how many pages and image files it checked.

2. For each `first picture not lazy` failure, open the page at phone width (375) and desktop width (1440) and see whether that picture is on screen when the page opens. If it is, the failure stands. If it is further down at both widths, say so and drop it.

3. Look at the main pictures of each page beside their alt text. Flag alt text that doesn't describe the picture or is stuffed with keywords (`appearance--google-images`, "Use descriptive filenames, titles, and alt text"). Also flag any picture that carries content but is set as a CSS background: Google doesn't index CSS images.

4. Confirm every Google quote in the report with `check_google_quote`.

## Report

One row per page: address and its failures. Then one list of image files to fix, heaviest first, each with what it needs: a WebP or AVIF version, a smaller size (in pixels wide), a descriptive name, width and height in the HTML, a supported format (HEIC or TIFF to JPEG, WebP or AVIF), or no lazy loading. A file used on many pages is listed once, with how many pages use it. List notices (such as a small favicon) last, one line each.
