The Application Cache, also known as AppCache,
is [deprecated](https://html.spec.whatwg.org/multipage/browsers.html#offline).

## How the Lighthouse Application Cache audit fails

[Lighthouse](https://developer.chrome.com/docs/lighthouse/overview.md.txt) flags pages that use the Application Cache:
![Lighthouse audit showing that a page uses the Application Cache](https://developer.chrome.com/static/docs/lighthouse/best-practices/appcache-manifest/image/lighthouse-audit-showing-2b37f1ff5bef4.png)

This audit fails when Lighthouse finds a reference to
the Application Cache manifest in a page's `<html>` tag.
For example, this markup causes the audit to fail:

```html
<html manifest="example.appcache">
  ...
</html>
```

> [!NOTE]
> **Note:** Each Best Practices audit is weighted equally in the Lighthouse Best Practices Score. Learn more in [The Best Practices
> score](https://developer.chrome.com/docs/lighthouse/performance/performance-scoring#best-practices).

## Use the Cache API instead of the Application Cache

To pass this audit,
remove the manifest from your page,
and use the
[Cache API](https://developer.mozilla.org/docs/Web/API/Cache)
via a [service worker](https://developer.chrome.com/docs/workbox/service-worker-overview.md.txt)
instead.

To migrate from the Application Cache to service workers,
consider using the
[sw-appcache-behavior library](https://github.com/GoogleChrome/sw-appcache-behavior).
This library generates a service-worker-based implementation of the behavior
defined in an Application Cache manifest.

See the [Current page does not respond with a 200 when offline](https://developer.chrome.com/docs/lighthouse/pwa/works-offline.md.txt) post
for more information about using service workers to make your site work
offline.

## Resources

- [Source code for **Uses Application Cache** audit](https://github.com/GoogleChrome/lighthouse/blob/ecd10efc8230f6f772e672cd4b05e8fbc8a3112d/lighthouse-core/audits/dobetterweb/appcache-manifest.js)
- MDN's [Cache](https://developer.mozilla.org/docs/Web/API/Cache) page
- [Current page does not respond with a 200 when offline](https://developer.chrome.com/docs/lighthouse/pwa/works-offline.md.txt)