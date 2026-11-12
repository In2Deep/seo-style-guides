![](https://developer.chrome.com/static/docs/lighthouse/overview/image/lighthouse-logo.svg)

[Lighthouse](https://github.com/GoogleChrome/lighthouse) is an open-source,
automated tool to help you improve the quality of web pages. You can run it on
any web page, public or requiring authentication. It has audits for performance,
accessibility, SEO, and more.

You can run Lighthouse in Chrome DevTools, from the command line, or as a Node
module. Give Lighthouse a URL to audit, it runs a series of audits against the page,
and then it generates a report on how well the page performed. Use the failed
audits as indicators for how to improve the page. Each audit has a reference
that explains why the audit is important, as well as how to fix it.

You can also use
[Lighthouse CI](https://github.com/GoogleChrome/lighthouse-ci/blob/main/docs/getting-started.md)
to prevent regressions on your sites.

[Video](https://www.youtube.com/watch?v=mLjxXPHuIJo)

## Get started

Choose the Lighthouse workflow that suits you best:

- [In Chrome DevTools](https://developer.chrome.com/docs/lighthouse/overview.md.txt#devtools). Audit pages that require authentication and read your reports in a user-friendly format, right from the browser.
- [From the command line](https://developer.chrome.com/docs/lighthouse/overview.md.txt#cli). Automate your Lighthouse runs with shell scripts.
- [As a Node module](https://developer.chrome.com/docs/lighthouse/overview.md.txt#programmatic). Integrate Lighthouse into your continuous integration systems.
- [From a web UI](https://developer.chrome.com/docs/lighthouse/overview.md.txt#psi). Run Lighthouse and link to reports, no installation needed.

> [!NOTE]
> **Note:** The CLI and Node workflows require you to have an instance of Google Chrome installed on your machine.

### Run Lighthouse in Chrome DevTools

Lighthouse has its own panel in Chrome DevTools. To run a report:

1. Download [Google Chrome for Desktop](https://www.google.com/chrome/browser/desktop/).
2. Open Chrome, and go to the URL you want to audit. You can audit any URL on the web.
3. [Open Chrome DevTools](https://developer.chrome.com/docs/devtools/open.md.txt).
4. Click the **Lighthouse** tab.

   <br />

   ![](https://developer.chrome.com/static/docs/lighthouse/overview/image/lighthouse-devtools.png) To the left is the viewport of the web page to be audited. The right is the Chrome DevTools **Lighthouse** panel.

   <br />

5. Click **Analyze page load**. DevTools shows you a list of audit categories.
   Leave them all enabled.

6. Click **Run audit**. After 30 to 60 seconds, Lighthouse gives you a report on
   the page.

   <br />

   ![](https://developer.chrome.com/static/docs/lighthouse/overview/image/lighthouse-report.png) A Lighthouse report in Chrome DevTools.

   <br />

### Install and run the Node command line tool

To install the Node module:

1. Download [Google Chrome for Desktop](https://www.google.com/chrome/browser/desktop/).
2. Install the current [Long-Term Support](https://github.com/nodejs/Release) version of [Node](https://nodejs.org).
3. Install Lighthouse. The `-g` flag installs it as a global module.

```bash
npm install -g lighthouse
```

To run an audit:

```bash
lighthouse <url>
```

To see all the options:

```bash
lighthouse --help
```

#### Run the Node module programmatically

See [Using programmatically](https://github.com/GoogleChrome/lighthouse/blob/master/docs/readme.md#using-programmatically)
for an example of running Lighthouse programmatically, as a Node module.

### Run PageSpeed Insights

To run Lighthouse on PageSpeed Insights:

1. Go to [PageSpeed Insights](https://pagespeed.web.dev/).
2. Enter a web page URL.
3. Click **Analyze**.

   <br />

   ![](https://developer.chrome.com/static/docs/lighthouse/overview/image/pagespeed-insights.png) The PageSpeed Insights website.

   <br />

### Run Lighthouse as a Chrome Extension

> [!CAUTION]
> **Caution:** Unless you have a specific reason, you should use [Chrome DevTools](https://developer.chrome.com/docs/lighthouse/overview.md.txt#devtools) rather than this Chrome Extension workflow. The DevTools workflow allows for testing local sites and authenticated pages, while the extension does not.

To install the extension:

1. Download [Google Chrome for Desktop](https://www.google.com/chrome/browser/desktop/).
2. Install the [Lighthouse Chrome Extension](https://chrome.google.com/webstore/detail/lighthouse/blipmdconlkpinefehnmjammfjpmpbjk) from the Chrome Webstore.

To run an audit:

1. In Chrome, go to the page you want to audit.
2. Click ![](https://developer.chrome.com/static/docs/lighthouse/overview/image/lighthouse-extension-icio-fffce0f9d83c.svg)
   **Lighthouse**, next to the Chrome address bar or in Chrome's extension menu.
   Once clicked, the Lighthouse menu expands.

   <br />

   ![](https://developer.chrome.com/static/docs/lighthouse/overview/image/lighthouse-extension-generate.png) The extension prompts you to generate a report.

   <br />

3. Click **Generate report**. Lighthouse runs its audits against the
   currently-focused page, then opens up a new tab with a report of the results.

   <br />

   ![](https://developer.chrome.com/static/docs/lighthouse/overview/image/lighthouse-report-extension.png) A Lighthouse report generated from the extension.

   <br />

## Share and view reports online

Use the [Lighthouse Viewer](https://googlechrome.github.io/lighthouse/viewer/)
to view and share reports online.
![](https://developer.chrome.com/static/docs/lighthouse/overview/image/lighthouse-report-viewer.png) The Lighthouse Viewer

### Share reports as JSON

The Lighthouse Viewer needs the JSON output of a Lighthouse report. Generate
the JSON outputs as follows:

- **From a Lighthouse report** . Click for the menu, then click ![](https://developer.chrome.com/static/docs/lighthouse/overview/image/save-json-button.svg) **Save as JSON**
- **Command line** . Run: `shell
  lighthouse --output json --output-path <path/for/output.json>`

To view the report data:

1. Open the [Lighthouse Viewer](https://googlechrome.github.io/lighthouse/viewer/).
2. Drag the JSON file onto the Viewer, or click anywhere in the Viewer to open your file navigator and select the file.

### Share reports as GitHub Gists

If you don't want to manually pass around JSON files, you can also share your
reports as secret GitHub gists. One benefit of gists is free version control.

To export a report as a gist from the report:

1. Click the menu, then click ![](https://developer.chrome.com/static/docs/lighthouse/overview/image/open-viewer-button.svg) **Open In Viewer** . The report is located at `https://googlechrome.github.io/lighthouse/viewer/`.
2. From the Viewer, click menu, then click ![](https://developer.chrome.com/static/docs/lighthouse/overview/image/open-viewer-button.svg) **Save as Gist**. The first time you do this, a popup asks permission to access your basic GitHub data, and to read and write to your gists.

To export a report as a gist from the CLI version of Lighthouse,
[manually create a gist](https://gist.github.com/) and copy-paste the report's
JSON output into the gist. The gist filename containing the JSON output must
end in `.lighthouse.report.json`. See [Share reports as JSON](https://developer.chrome.com/docs/lighthouse/overview.md.txt#json) for an
example of how to generate JSON output from the command line tool.

To view a report that's been saved as a gist:

- Add `?gist=<ID>` to the Viewer's URL, where `<ID>` is the ID of the gist. `text
  https://googlechrome.github.io/lighthouse/viewer/?gist=<ID>`
- Open the [Viewer](https://googlechrome.github.io/lighthouse/viewer/), and paste the URL of a gist into it.

## Lighthouse extensibility

Lighthouse aims to provide guidance that is relevant and actionable for all web
developers. To this end, there are two features available that allow you to
tailor Lighthouse to your specific needs.

### Stack packs

Developers use many different technologies (backend, content management systems,
and JavaScript frameworks) to build their web pages. Instead of surfacing
general recommendations, Lighthouse provides relevant and actionable advice,
depending on the tools used.

*Stack packs* allow Lighthouse to detect what platform your site is built on
and display specific stack-based recommendations. These recommendations are
defined and curated by experts from the community.

To contribute a stack pack, review the
[Contributing Guidelines](https://github.com/GoogleChrome/lighthouse-stack-packs/blob/master/CONTRIBUTING.md).

### Lighthouse plugins

Lighthouse plugins allow domain experts to extend the functionality of
Lighthouse for their community's specific needs. You can leverage
the data that Lighthouse collects to create new audits. At its core, a
Lighthouse plugin is a node module that implements a set of checks to be run by
Lighthouse and added to the report as a new category.

For more information about how to create your own plugin, check out our
[Plugin Handbook](https://github.com/GoogleChrome/lighthouse/blob/master/docs/plugins.md)
in the Lighthouse GitHub repo.

## Integrate Lighthouse

If you're a company or an individual who is integrating Lighthouse as part of
the products or services you're offering, that's great! We want as many people
as possible to use Lighthouse.

Refer to the
[Guidelines and Brand Assets for Integrating Lighthouse](https://docs.google.com/document/d/e/2PACX-1vRWKW9RiB3suYt1KqgBJhwLnvV-AiFne8iAudADtwK-LWLNParYsFts92InHNtB_BV5x-xtSVcnTO2n/pub)
to show that Lighthouse is used, while protecting our brand.

## Contribute to Lighthouse

Lighthouse is open source and
[contributions are welcome](https://github.com/GoogleChrome/lighthouse/blob/master/CONTRIBUTING.md)!
Check out the repository's
[Issue tracker](https://github.com/GoogleChrome/lighthouse/issues) to find
[bugs that you can fix](https://github.com/GoogleChrome/lighthouse/labels/good%20first%20issue),
or audits that you can create or improve upon. The Issues are a good place to
discuss performance metrics, ideas for new audits, or anything else related to
Lighthouse.