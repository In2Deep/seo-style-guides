---
name: images
description: Find image problems on a website against Google's guides. Checks every page for missing width and height, a wrong shape, files much bigger than they show, JPEG or PNG with no WebP or AVIF version, formats Google Images can't use (such as HEIC), camera or generic file names, missing or file name alt text, a lazy loaded first picture, small structured data images and a favicon Google can't use. Use when asked to check, review or audit a site's images or pictures, for a whole site, a local preview, or one built HTML file. It reports only; converting, resizing or renaming images is a separate request.
argument-hint: <address or HTML file>
---

# Image check

The argument is the address to check, for example `https://example.com` or `http://127.0.0.1:4321/`, or a built HTML file such as `dist/index.html`. An address covers every page under it, up to 500 pages; say so if the checker reports it stopped at that limit. Without an argument, ask which address.

This skill reports. Don't change, convert, resize or rename any file unless the user then asks for fixes.

A site behind a login can't be checked. Don't enter a password; ask for the address of a local preview of the same build instead.

## Steps

1. Run the image checker with Python 3.10 or newer, putting the address or file in quotes, for example:

   ```sh
   python3 -B "${CLAUDE_PLUGIN_ROOT}/image_check.py" "https://example.com/"
   ```

   If this skill is not running from an installed plugin, `image_check.py` is at the root of the seo-style-guides repository. If `python3` is older than 3.10, use a newer one (for example `python3.13`). The checker runs 10 checks on every page, each with the Google quote it rests on, opens every image file (up to 30 MB of each) to read its type and pixel size, and lists every problem it finds. It reads the HTML only, not CSS, so a size or shape set in CSS is not seen. Say how many pages and image files it checked.

2. Set the viewport to phone width (375) or desktop width (1440), then load the page at that size. After the page loads and before scrolling or clicking, run this to observe the Largest Contentful Paint element for three seconds. Repeat with a fresh load at the other width:

   ```js
   await new Promise(resolve => {
     if (!globalThis.PerformanceObserver?.supportedEntryTypes?.includes("largest-contentful-paint")) {
       resolve(null);
       return;
     }
     let latest;
     const observer = new PerformanceObserver(list => {
       latest = list.getEntries().at(-1) ?? latest;
     });
     observer.observe({type: "largest-contentful-paint", buffered: true});
     setTimeout(() => {
       const element = (observer.takeRecords().at(-1) ?? latest)?.element;
       observer.disconnect();
       resolve(element ? {tag: element.tagName, src: element.currentSrc || "", lazy: element.loading === "lazy"} : null);
     }, 3000);
   });
   ```

   Report a measured `<img loading="lazy">` as a failure. Clear a static flag only when both viewports have a measured LCP on another element and the flagged image has finished loading wherever it is visible. Treat a `null` result or a visible image still loading as inconclusive.

3. Look at the main pictures of each page beside their alt text. Flag alt text that doesn't describe the picture or is stuffed with keywords (`appearance--google-images`, "Use descriptive filenames, titles, and alt text"). Also flag any picture that carries content but is set as a CSS background: Google doesn't index CSS images.

4. Confirm every Google quote in the report with `check_google_quote`.

## Report

One row per page: address and its failures. Then one list of image files to fix, heaviest first where the checker gave a size (files with no size listed after), each with what it needs: a WebP or AVIF version, a smaller size (in pixels wide), a descriptive name, width and height in the HTML (or on its `<source>`), a supported format (HEIC to JPEG, WebP or AVIF), a repaired or replaced file, or no lazy loading. A file used on many pages is listed once, with how many pages use it. List notices (such as a small favicon) last, one line each.
