Minifying JavaScript files can reduce payload sizes and script parse time.
The Opportunities section of your Lighthouse report lists
all unminified JavaScript files,
along with the potential savings in [kibibytes (KiB)](https://en.wikipedia.org/wiki/Kibibyte)
when these files are minified:
![A screenshot of the Lighthouse Minify JavaScript audit](https://developer.chrome.com/static/docs/lighthouse/performance/unminified-javascript/image/a-screenshot-the-lightho-e35d561e16c6f.png)

## How to minify your JavaScript files

Minification is the process of removing whitespace and any code that is not necessary
to create a smaller but perfectly valid code file.
[Terser](https://github.com/terser-js/terser) is a popular JavaScript compression tool.
webpack v4 includes a plugin for this library by default to create minified build files.

## Stack-specific guidance

### Drupal

Ensure you have enabled **Aggregate JavaScript files** in the **Administration \>\> Configuration \>\> Development** page.

### Joomla

A number of [Joomla extensions](https://extensions.joomla.org/instant-search/?jed_live%5Bquery%5D=performance)
can speed up your site by concatenating, minifying, and compressing your
scripts. There are also templates that provide this functionality.

### Magento

Use [Terser](https://www.npmjs.com/package/terser) to minify all JavaScript
assets from static content deployment, and disable the built-in minification
feature.

### React

If your build system minifies JS files automatically, ensure that you are
deploying the [production build](https://reactjs.org/docs/optimizing-performance.html#use-the-production-build)
of your application. You can check this with the React Developer Tools
extension.

### WordPress

A number of [WordPress plugins](https://wordpress.org/plugins/search/minify+javascript/) can speed up
your site by concatenating, minifying, and compressing your scripts. You may
also want to use a build process to do this minification up front if possible.

## Resources

- [Source code for **Minify JavaScript** audit](https://github.com/GoogleChrome/lighthouse/blob/main/core/audits/byte-efficiency/unminified-javascript.js)