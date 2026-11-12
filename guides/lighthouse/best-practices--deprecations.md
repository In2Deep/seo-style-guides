Deprecated APIs are scheduled to be removed from Chrome.
Calling these APIs
after they're removed causes errors on your site.

## How the Lighthouse deprecated API audit fails

[Lighthouse](https://developer.chrome.com/docs/lighthouse/overview.md.txt) flags pages that call deprecated APIs:
![Lighthouse audit shows usage of deprecated APIs](https://developer.chrome.com/static/docs/lighthouse/best-practices/deprecations/image/lighthouse-audit-shows-us-2c6f01ea0d796.png)

Lighthouse includes all deprecated API warnings that Chrome logs
to the DevTools Console.

> [!NOTE]
> **Note:** Each Best Practices audit is weighted equally in the Lighthouse Best Practices Score. Learn more in [The Best Practices
> score](https://developer.chrome.com/docs/lighthouse/performance/performance-scoring#best-practices).

## How to remove deprecated APIs

Go to
[Chrome Platform Status](https://www.chromestatus.com/features#deprecated) and
expand the entries for the APIs that you're using
to learn why the APIs are deprecated and how to replace them.

## Resources

- [Source code for **Uses deprecated APIs** audit](https://github.com/GoogleChrome/lighthouse/blob/main/core/audits/deprecations.js)
- [Chrome Platform Status](https://www.chromestatus.com/features#deprecated)