> [!CAUTION]
> **Caution:** PWA testing in Lighthouse is deprecated. For more information on its deprecation see [Chrome's updated Installability Criteria](https://developer.chrome.com/blog/update-install-criteria.md.txt). For guidance on testing, refer to the [PWA documentation.](https://developer.chrome.com/docs/devtools/progressive-web-apps.md.txt)

The [Core Progressive Web App checklist](https://web.dev/pwa-checklist#core) says that a PWA
should provide a custom offline page. The [Optimial Progressive Web App checklist](https://web.dev/pwa-checklist#optimal)
says that a PWA should provide an offline experience where the PWA works the same offline as
it does online (wherever network connectivity isn't strictly required).

Learn more in the [What is network reliability and how do you measure it?](https://web.dev/articles/network-connections-unreliable) post.

## How the Lighthouse offline audit fails

[Lighthouse](https://developer.chrome.com/docs/lighthouse/overview.md.txt)
flags pages that don't respond with an
[HTTP 200 response](https://developer.mozilla.org/docs/Web/HTTP/Status#Successful_responses)
when offline:
![Lighthouse audit showing page doesn't respond with a 200 when offline](https://developer.chrome.com/static/docs/lighthouse/pwa/works-offline/image/lighthouse-audit-showing-8370440b1b50a.png)

Lighthouse emulates an offline connection using the [Chrome Remote Debugging Protocol](https://github.com/ChromeDevTools/devtools-protocol)
and then attempts to retrieve the page using [`XMLHttpRequest`](https://developer.mozilla.org/docs/Web/API/XMLHttpRequest).

> [!NOTE]
> **Note:** In the Lighthouse report UI the full PWA badge is given when you pass all of the audits in all of the PWA subcategories (**Fast and reliable** , **Installable** , and **PWA optimized**).

## How to make your PWA work offline

> [!TIP]
> **Success:** [Workbox](https://developer.chrome.com/docs/workbox) is the recommended approach for adding service workers to websites because it automates a lot of boilerplate, makes it easier to follow best practices, and prevents subtle bugs that are common when using the low-level `ServiceWorker` API directly.

1. Add a [service worker](https://developer.chrome.com/docs/workbox/service-worker-overview.md.txt) to your app.
2. Use the service worker to cache files locally.
3. When offline, use the service worker as a network proxy to return the locally cached version of the file.

> [!WARNING]
> **Try it:** Learn how to add a service worker to your app with the [Working with service workers](https://web.dev/codelab-service-workers) codelab.

## Resources

- [What is network reliability and how do you measure it?](https://web.dev/articles/network-connections-unreliable)
- [Service Workers: an Introduction](https://developer.chrome.com/docs/workbox/service-worker-overview.md.txt)