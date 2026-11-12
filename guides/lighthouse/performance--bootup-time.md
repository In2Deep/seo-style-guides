When your JavaScript takes a long time to execute,
it slows down your page performance in several ways:

- **Network cost**

  More bytes equals longer download times.
- **Parse and compile cost**

  JavaScript gets parsed and compiled on the main thread.
  When the main thread is busy, the page can't respond to user input.
- **Execution cost**

  JavaScript is also executed on the main thread.
  If your page runs a lot of code before it's really needed,
  that also delays your [Time To Interactive](https://web.dev/articles/tti),
  which is one of the key metrics related to how users perceive your page speed.
- **Memory cost**

  If your JavaScript holds on to a lot of references,
  it can potentially consume a lot of memory.
  Pages appear janky or slow when they consume a lot of memory.
  Memory leaks can cause your page to freeze up completely.

## How the Lighthouse JavaScript execution time audit fails

[Lighthouse](https://developer.chrome.com/docs/lighthouse/overview.md.txt)
shows a warning when JavaScript execution takes longer than 2 seconds.
The audit fails when execution takes longer than 3.5 seconds:
![A screenshot of the Lighthouse Reduce JavaScript execution time audit](https://developer.chrome.com/static/docs/lighthouse/performance/bootup-time/image/a-screenshot-the-lightho-c3740d2b20198.png)

To help you identify the biggest contributors to execution time,
Lighthouse reports the time spent executing, evaluating, and parsing
each JavaScript file that your page loads.

> [!NOTE]
> **Note:** See the [Lighthouse performance scoring](https://developer.chrome.com/docs/lighthouse/performance/performance-scoring.md.txt) post to learn how your page's overall performance score is calculated.

## How to speed up JavaScript execution

- [Only send the code that your users need by implementing code splitting](https://web.dev/articles/reduce-javascript-payloads-with-code-splitting).
- [Minify and compress your code](https://web.dev/articles/reduce-network-payloads-using-text-compression).
- [Remove unused code](https://web.dev/articles/remove-unused-code).
- [Reduce network trips by caching your code with the PRPL pattern](https://web.dev/articles/apply-instant-loading-with-prpl).

For other ways to improve page load, check out the
[Performance audits landing page](https://developer.chrome.com/docs/lighthouse/performance).

## Resources

[Source code for **Reduce JavaScript execution time** audit](https://github.com/GoogleChrome/lighthouse/blob/main/core/audits/bootup-time.js)