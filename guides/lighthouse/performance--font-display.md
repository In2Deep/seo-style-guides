> [!WARNING]
> **Warning:** This audit has moved into the [Font display](https://developer.chrome.com/docs/performance/insights/font-display.md.txt) insight as of Lighthouse 13. For more information see [What's new in Lighthouse 13](https://developer.chrome.com/blog/lighthouse-13-0.md.txt).

Fonts are often large files with slow load times.
Some browsers hide text until the font loads,
causing a [flash of invisible text (FOIT)](https://web.dev/articles/avoid-invisible-text).

## How the Lighthouse font-display audit fails

[Lighthouse](https://developer.chrome.com/docs/lighthouse/overview.md.txt)
flags any font URLs that may flash invisible text:
![A screenshot of the Lighthouse Ensure text remains visible during webfont loads audit](https://developer.chrome.com/static/docs/lighthouse/performance/font-display/image/a-screenshot-the-lightho-15d52429afc09.png)

> [!NOTE]
> **Note:** See the [Lighthouse performance scoring](https://developer.chrome.com/docs/lighthouse/performance/performance-scoring.md.txt) post to learn how your page's overall performance score is calculated.

## How to avoid showing invisible text

The [`font-display` API](https://developer.mozilla.org/docs/Web/CSS/@font-face/font-display) indicates
how a font is displayed when used inside a `font-face` style. The following
`font-display` values will tell the browser to use a system font if the custom font is not ready:

- `swap`
- `optional`
- `fallback`

### CSS Example

```css
@font-face {
  font-family: 'Pacifico';
  font-style: normal;
  font-weight: 400;
  src: local('Pacifico Regular'), local('Pacifico-Regular'),
    url(https://fonts.gstatic.com/s/pacifico/v12/FwZY7-Qmy14u9lezJ-6H6MmBp0u-.woff2)
      format('woff2');
  font-display: swap;
}
```

### Google Fonts Example

Add the `&display=swap`/`&display=optional`/`&display=fallback` [parameter](https://developer.mozilla.org/docs/Learn/Common_questions/What_is_a_URL#Basics_anatomy_of_a_URL) to the end of your Google Fonts URL:

```html
<link
  href="https://fonts.googleapis.com/css?family=Roboto:400,700&display=swap"
  rel="stylesheet"
/>
```

### How to avoid layout shifts caused by deferred fonts

Temporarily showing a system font will replace a FOIT with a flash of unstyled text (FOUT). This improves FCP\&LCP by rendering content sooner,
but FOIT and FOUT will both have the same impact on CLS when the custom font replaces the temporary system font.

The CLS impact of font loading can be mitigated using [preloads in conjunction with `font-display: optional`](https://web.dev/articles/preload-optional-fonts).
However, overusing preloads can negatively impact load metrics. We recommend performing A/B testing to ensure that preloading fonts does not introduce any
performance regressions.

## Stack-specific guidance

### Drupal

Specify `@font-display` when defining custom fonts in your theme.

### Magento

Specify `@font-display` when [defining custom fonts](https://devdocs.magento.com/guides/v2.3/frontend-dev-guide/css-topics/using-fonts.html).

## Resources

- [Source code for **Ensure text remains visible during webfont load** audit](https://github.com/GoogleChrome/lighthouse/blob/main/core/audits/font-display.js)
- [Avoid invisible text during loading](https://web.dev/articles/avoid-invisible-text)
- [Controlling font performance with font displays](https://developer.chrome.com/blog/font-display.md.txt)
- [Preload web fonts to improve loading speed (codelab)](https://web.dev/articles/codelab-preload-web-fonts)
- [Prevent layout shifting and flashes of invisible text (FOIT) by preloading optional fonts](https://web.dev/articles/preload-optional-fonts)