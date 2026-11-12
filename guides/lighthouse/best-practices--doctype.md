Specifying a doctype prevents the browser from switching to
[quirks mode](https://developer.mozilla.org/docs/Web/HTML/Quirks_Mode_and_Standards_Mode),
which can cause your page to [render in unexpected ways](https://quirks.spec.whatwg.org/#css).

## How the Lighthouse doctype audit fails

[Lighthouse](https://developer.chrome.com/docs/lighthouse/overview.md.txt) flags pages without the
`<!DOCTYPE html>` declaration:
![](https://developer.chrome.com/static/docs/lighthouse/best-practices/doctype/image/lighthouse-audit-showing-156167946cd09.png) Lighthouse audit showing missing doctype.

> [!NOTE]
> **Note:** Each Best Practices audit is weighted equally in the Lighthouse Best Practices Score. Learn more in [The Best Practices
> score](https://developer.chrome.com/docs/lighthouse/performance/performance-scoring#best-practices).

## How to add a doctype declaration

Add the `<!DOCTYPE html>` declaration to the top of your HTML document:

```html
<!DOCTYPE html>
<html lang="en">
...
```

Read about [Doctype on MDN](https://developer.mozilla.org/docs/Glossary/Doctype)
for more information.

## Resources

- [Source code for **Page lacks the HTML doctype, thus triggering quirks mode** audit](https://github.com/GoogleChrome/lighthouse/blob/main/core/audits/dobetterweb/doctype.js)
- [Quirks Mode and Standards Mode](https://developer.mozilla.org/docs/Web/HTML/Quirks_Mode_and_Standards_Mode)