# Accessibility metadata vocabulary

The values the `schema` skill may draft for schema.org's accessibility properties, and when each
one is true of a web page.

Sources:

- Schema.org Accessibility Properties for Discoverability Vocabulary 1.1, Final Community Group
  Report, 24 August 2026: <https://www.w3.org/2021/a11y-discov-vocab/latest/>. It is a W3C
  Community Group report, not a W3C Standard. The repo keeps a copy as the `a11y-vocab` guide,
  `guides/a11y-vocab/index.md`. This file summarizes it. The saved copy is the authority: where
  they differ, follow the copy. If `check_google_docs` finds the W3C has published a newer
  version, update this file too.
- The properties on schema.org, for example <https://schema.org/accessibilityFeature>. Schema.org
  allows all seven properties on `CreativeWork` and its subtypes only.

Google Search doesn't use these properties. No Google guide in this repository documents them.

## WCAG 2.2

The vocabulary cites success criteria by their undated WCAG 2 address, <https://www.w3.org/TR/WCAG2/>,
which is WCAG 2.2. Every criterion this file names (1.3.2, 1.4.5, 1.4.6, 1.4.7, 2.3.1) is in WCAG 2.2
with the same number.

Schema.org has no property for a WCAG conformance claim. The vocabulary puts one in
`accessibilitySummary`, for example "This publication meets WCAG 2.1 Level AA." Draft "WCAG 2.2
Level AA", or any level, only when the site's own accessibility statement makes that claim. This
skill doesn't test conformance: WCAG 2.2 has 78 success criteria, and checking them needs a full
accessibility audit.

## Where they go

Add them to the item that describes the page's main content, if it is a `CreativeWork`: for example
`Article`, `BlogPosting`, `NewsArticle`, `VideoObject`, `Book`, `Course`, `DigitalDocument`,
`Recipe`, `WebPage`, or `FAQPage`. Never add them to a type that isn't a `CreativeWork`, such as
`Product`, `Organization`, `LocalBusiness`, `Event`, or `Person`.

Each property except `accessibilitySummary` takes a list. Write a JSON array even for one value.

## accessMode

How the content's information is encoded, before any alternatives. Values: `auditory`, `tactile`,
`textual`, `visual`.

| Value | Set it when the page shows |
|---|---|
| `textual` | Main content in text. Not when the only text is navigation, such as a menu or table of contents. |
| `visual` | Images, charts, diagrams or video that carry information. Not for logos, cover images or decoration. |
| `auditory` | Audio or video whose sound carries information. Not for background music. |
| `tactile` | Information in tactile form. A web page almost never has it. |

Visual content indicators, set in addition to `visual`, never instead of it: `chartOnVisual`,
`chemOnVisual`, `colorDependent`, `diagramOnVisual`, `mathOnVisual`, `musicOnVisual`,
`textOnVisual`.

## accessModeSufficient

Each way to take in all of the content, including its alternatives. The value is a list of
`ItemList` items. Each item lists one or more of `auditory`, `tactile`, `textual`, `visual`:

```json
"accessModeSufficient": [
  {"@type": "ItemList", "itemListElement": ["textual", "visual"], "description": "Text and images"},
  {"@type": "ItemList", "itemListElement": ["textual"], "description": "Text only"}
]
```

Draft a text-only item only when every informative image has a text alternative, and every audio
or video item has a transcript or captions. The vocabulary says the single-mode items are the most
important ones to list.

## accessibilityFeature

The accessibility features the content has. Draft only values that are true of the page.

| Value | True of a web page when |
|---|---|
| `alternativeText` | Every informative image has an `alt` attribute that describes it. `alt=""` on decorative images is fine. |
| `longDescription` | Complex images, charts, tables or diagrams have a full description on the page or linked from it. |
| `transcript` | Every audio or video item has a transcript on the page or linked from it. |
| `closedCaptions` | Every video has captions the viewer can turn off, such as `<track kind="captions">` or a player that shows its CC control. |
| `openCaptions` | Captions are part of the video image. HTML can't show this, so it needs a true value from the owner. |
| `audioDescription` | Video has audio description, such as `<track kind="descriptions">` or a described version. |
| `signLanguage` | Video has sign language interpretation. Name the sign language in `accessibilitySummary`. |
| `structuralNavigation` | The headings fully and accurately reflect the page's structure. |
| `tableOfContents` | The page has a table of contents that links to its major sections. |
| `index` | The content has an index. |
| `ARIA` | The page uses ARIA document structure, landmark, live region or window roles. |
| `MathML` | Math is marked up as `<math>`. |
| `MathML-chemistry`, `latex`, `latex-chemistry`, `ChemML` | Math or chemistry is encoded in that markup. |
| `ttsMarkup` | SSML, a pronunciation lexicon, or CSS Speech is used for text-to-speech. |
| `synchronizedAudioText` | Audio and text are synchronized for playback together. |
| `timingControl` | Users can pause or reset all timed interaction. |
| `pageBreakMarkers`, `pageNavigation` | The content has static page break markers, or a way to go to them, for example a book with print page numbers. |
| `taggedPDF` | A PDF's tagging conforms to PDF/UA. Not for HTML. |
| `unlocked` | No DRM or other content restriction is applied. |

The owner has to confirm these, because the HTML alone can't prove them:

- `readingOrder`: the markup order matches the visual order (WCAG 1.3.2).
- `displayTransformability`: users can change colors, fonts, spacing and alignment. Nothing may
  prevent it, such as `style` attributes or `!important`. Text isn't shown as images.
- `highContrastDisplay`: text contrast meets WCAG 1.4.6 (Enhanced).
- `highContrastAudio`: speech meets WCAG 1.4.7.
- `largePrint`: the content is formatted to large print guidelines. Not set just because text can
  be enlarged.

Tactile terms: `braille`, `tactileGraphic`, `tactileObject`. Internationalization terms:
`fullRubyAnnotations`, `rubyAnnotations`, `horizontalWriting`, `verticalWriting`,
`withAdditionalWordSegmentation`, `withoutAdditionalWordSegmentation`.

`none` means the content has no accessibility features. `unknown` means nobody has checked yet.
Neither may be set with any other feature value. Don't draft either one.

Deprecated values, which an existing page may still use:

| Deprecated | Use instead |
|---|---|
| `captions` | `closedCaptions` or `openCaptions` |
| `bookmarks` | `tableOfContents` (for PDF bookmarks) |
| `annotations` | nothing |
| `printPageNumbers` (a synonym, not formally deprecated) | `pageBreakMarkers` |

## accessibilityHazard

Whether the content can physically harm some users.

| Kind | Values |
|---|---|
| Hazards | `flashing` (meets the WCAG 2.3.1 thresholds), `motionSimulation`, `sound` |
| No hazard | `none` (no hazard of any kind), `noFlashingHazard`, `noMotionSimulationHazard`, `noSoundHazard` |
| Unknown | `unknown`, `unknownFlashingHazard`, `unknownMotionSimulationHazard`, `unknownSoundHazard` |

Don't combine values that contradict each other:

- A hazard never goes with its own "no" or "unknown" value, or with `none` or `unknown`.
- `none` and `unknown` each go alone.
- Use `none` rather than listing all three "no" values.

The HTML alone can't show whether a page has a hazard. Draft a hazard value only when the page or
the owner says so. Otherwise list it as needing a true value.

## accessibilitySummary

A free-text description of the content's accessibility, including what is missing. For example,
"Short descriptions are present but long descriptions will be needed for non-visual users."

Take it only from text the site already publishes, such as an accessibility statement. Never write
a conformance claim, such as "meets WCAG 2.1 AA", that the site doesn't make.

## accessibilityAPI and accessibilityControl

These are for documents tied to one application, such as a word processing file. The vocabulary
says they are not a useful indicator for an HTML document. Don't draft them for web pages.
