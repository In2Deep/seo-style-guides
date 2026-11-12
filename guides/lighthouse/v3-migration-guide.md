This guide is for Lighthouse v2 users who:

- Run Lighthouse from Node or the command line.
- Rely on the JSON output of Lighthouse.

If these do not apply to you, then your workflow for running Lighthouse is mostly the same. See [Announcing Lighthouse 3.0](https://developer.chrome.com/blog/lighthouse3.md.txt) for an overview of new features and changes.

## Invocation changes

Lighthouse now computes simulated performance by default and throttling settings have been heavily changed.

### CLI Flags

| Scenario | v2 Flags | v3 Flags |
|---|---|---|
| DevTools 3G Throttling | None (default behavior) | `--throttling-method=devtools` |
| No Throttling | `--disable-network-throttling --disable-cpu-throttling` | `--throttling-method=provided` |
| Network Throttling, No CPU Throttling | `--disable-cpu-throttling` | `--throttling-method=devtools --throttling.cpuSlowdownMultiplier=1` |
| Run Performance Audits | `--perf` | `--preset=perf` |
| Run Mixed Content Audits | `--mixed-content` | `--preset=mixed-content` |

### Node Module

In Lighthouse v3, the Node module accepts the same configuration options as the CLI. This is a breaking change in the sense that many of these options were ignored in v2, whereas now they'll actually affect how Lighthouse runs.

```javascript
const fs = require('fs');
const lighthouse = require('lighthouse');
async function run() {
  // `onlyCategories` was previously only available as a config setting.
  // `output` was previously only available in CLI.
  const flags = {onlyCategories: ['performance'], output: 'html'};
  const html = (await lighthouse('https://google.com/', flags)).report;
  fs.writeFileSync('report.html', html);
}
```

## Output changes

### New, top-level format in JSON output

The JSON object that Lighthouse v3 returns now contains three top-level properties:

- `lhr`. The results of the audits. Short for "Lighthouse Results". This was essentially the top-level object in v2, but v3 introduces breaking changes to the shape of this object, too. See [Changes to the results object](https://developer.chrome.com/docs/lighthouse/v3-migration-guide.md.txt#lhr).
- `artifacts`. The data collected from Chrome while auditing. This was previously intermingled with the properties of the LHR.
- `report`. The formatted report HTML/JSON/CSV as a string.

### Changes to the results object

As mentioned in [New, top-level format in JSON output](https://developer.chrome.com/docs/lighthouse/v3-migration-guide.md.txt#json), the results of audits are no available via the `lhr` property. In v2, the contents of this object were essentially the top-level JSON output. However, the shape of this object itself has changed in v3. The table below lists all the changes.

- If a row has a value in both **v2** and **v3** columns, it means that you should replace any reference to the v2 property in your code with the v3-equivalent.
- When a row does not have a value in the **v3** column, the **Notes** column describes your options.
- Note that items such as <var translate="no">ID</var> represent placeholder text.

| v2 Property | v3-Equivalent | Notes |
|---|---|---|
| `initialUrl` | `requestedUrl` |   |
| `url` | `finalUrl` |   |
| `generatedTime` | `fetchedTime` |   |
| `reportCategories` | `categories` | Changed from array to a keyed object. |
| `reportGroups` | `categoryGroups` |   |
| `audits.ID.name` | `audits.ID.id` |   |
| `audits.ID.description` | `audits.ID.title` |   |
| `audits.ID.helpText` | `audits.ID.description` |   |
| `audits.ID.scoringMode` | `audits.ID.scoreDisplayMode` | Possible values have been expanded to `numeric|binary|manual|informative|not-applicable|error`. |
| `audits.ID.score` | `audits.ID.score` | Scores are always a number between 0 and 1 (not 0-100) when `scoreDisplayMode` is numeric or binary. Scores are always `null` for other display modes as there is no notion of pass/fail. |
| `audits.ID.displayValue` | `audits.ID.displayValue` | Can now be an array of printf-style arguments for string interpolation. |
| `audits.ID.debugString` | `audits.ID.explanation` `audits.ID.errorMessage` `audits.ID.warnings` | `debugString` values have been converted to one of the three properties above depending on their intent. |
| `audits.ID.details` | `audits.ID.details` | Structure of details has shifted to be more consumable. Each entry in `.items` is an object with reliable keys instead of `any[]`. |
| `audits.ID.error` | `audits.ID.scoreDisplayMode === 'error'` |   |
| `audits.ID.notApplicable` | `audits.ID.scoreDisplayMode === 'not-applicable'` |   |
| `audits.ID.informative` | `audits.ID.scoreDisplayMode === 'informative'` |   |
| `audits.ID.manual` | `audits.ID.scoreDisplayMode === 'manual'` |   |
| `audits.ID.extendedInfo` |   | Removed. Use `details` instead. |