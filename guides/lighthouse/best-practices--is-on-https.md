All sites should be protected with HTTPS, even ones that don't handle sensitive data. This includes avoiding [mixed content](https://web.dev/articles/what-is-mixed-content), where some resources are loaded over HTTP despite the initial request being served over HTTPS. HTTPS prevents intruders from tampering with or passively listening in on the communications between your app and your users, and is a prerequisite for HTTP/2 and many new web platform APIs.

For more information about why all sites should be protected with HTTPS, see
[Why HTTPS Matters](https://web.dev/articles/why-https-matters).

## How the Lighthouse HTTPS audit fails

[Lighthouse](https://developer.chrome.com/docs/lighthouse/overview.md.txt)
flags pages that aren't on HTTPS:
![Lighthouse audit showing page isn't on HTTPS](https://developer.chrome.com/static/docs/lighthouse/best-practices/is-on-https/image/lighthouse-audit-showing-8a30623c5456f.png)

## How to migrate your site to HTTPS

Consider hosting your site on a CDN. Most CDNs are secure by default.

To learn how to enable HTTPS on your servers, see Google's
[Enabling HTTPS on Your Servers](https://web.dev/articles/enable-https).
If you're running your own server and need a cheap and easy way to generate
certificates, [Let's Encrypt](https://letsencrypt.org/) is a good option.

If your page is already running on HTTPS but you're failing this audit,
you may have problems with [mixed content](https://web.dev/articles/what-is-mixed-content).
A page has mixed content when the page itself is loaded over HTTPS,
but it requests an unprotected (HTTP) resource. Check out the following doc on the
Chrome DevTools Security panel to learn how to debug these situations:
[Understand Security Issues With Chrome DevTools](https://developer.chrome.com/docs/devtools/security.md.txt).

## Resources

- [Source code for **Does not use HTTPS** audit](https://github.com/GoogleChrome/lighthouse/blob/main/core/audits/is-on-https.js)
- [Why You Should Always Use HTTPS](https://web.dev/articles/why-https-matters)
- [Enabling HTTPS on Your Servers](https://web.dev/articles/enable-https)
- [Understand Security Issues With Chrome DevTools](https://developer.chrome.com/docs/devtools/security.md.txt)
- [What Is Mixed Content?](https://web.dev/articles/what-is-mixed-content)
- [Let's Encrypt](https://letsencrypt.org/)