Source: <https://www.w3.org/community/reports/a11y-discov-vocab/CG-FINAL-vocabulary-20260824/>

Converted from HTML to Markdown by `sync_google_docs.py`.

# Schema.org Accessibility Properties for Discoverability Vocabulary 1.1

[Final Community Group Report](https://www.w3.org/standards/types#reports) 24 August 2026

- This version:

<https://www.w3.org/community/reports/a11y-discov-vocab/CG-FINAL-vocabulary-20260618/>

- Previous version:

<https://www.w3.org/community/reports/a11y-discov-vocab/CG-FINAL-vocabulary-20260326/>

- Latest published version:

<https://www.w3.org/2021/a11y-discov-vocab/latest/>

- Latest editor's draft:

<https://w3c-cg.github.io/a11y-discov-vocab/>

- Editors:

Charles LaPierre ([Benetech](https://benetech.org))

Madeleine Rothberg ([WGBH](https://www.wgbh.org))

Matt Garrish ([DAISY Consortium](https://daisy.org))

- Feedback:

[GitHub w3c-cg/a11y-discov-vocab](https://github.com/w3c-cg/a11y-discov-vocab/) ([pull requests](https://github.com/w3c-cg/a11y-discov-vocab/pulls/), [new issue](https://github.com/w3c-cg/a11y-discov-vocab/issues/new/choose), [open issues](https://github.com/w3c-cg/a11y-discov-vocab/issues/))

[Copyright](https://www.w3.org/policies/#copyright) © 2026 the Contributors to the Schema.org Accessibility Properties for Discoverability Vocabulary 1.1 Specification, published by the [Accessibility Discoverability Vocabulary for Schema.org Community Group](https://www.w3.org/groups/cg/a11y-discov-vocab) under the [W3C Community Final Specification Agreement (FSA)](https://www.w3.org/community/about/agreements/fsa/). A human-readable [summary](https://www.w3.org/community/about/agreements/fsa-deed/) is available.

---

## Abstract

This document defines the recommended vocabularies for use with the Schema.org accessibility properties for discoverability of creative works.

## Status of This Document

This specification was published by the [Accessibility Discoverability Vocabulary for Schema.org Community Group](https://www.w3.org/groups/cg/a11y-discov-vocab). It is not a W3C Standard nor is it on the W3C Standards Track. Please note that under the [W3C Community Final Specification Agreement (FSA)](https://www.w3.org/community/about/agreements/final/) other conditions apply. Learn more about [W3C Community and Business Groups](https://www.w3.org/community/).

[GitHub Issues](https://github.com/w3c-cg/a11y-discov-vocab/issues/) are preferred for discussion of this specification.

## 1. Introduction

### 1.1 Background

The [CreativeWork type](https://schema.org/CreativeWork) [schema-org] includes the following accessibility properties for discoverability:

- [accessibilityAPI](https://schema.org/accessibilityAPI)

- [accessibilityControl](https://schema.org/accessibilityControl)

- [accessibilityFeature](https://schema.org/accessibilityFeature)

- [accessibilityHazard](https://schema.org/accessibilityHazard)

- [accessibilitySummary](https://schema.org/accessibilitySummary)

- [accessMode](https://schema.org/accessMode)

- [accessModeSufficient](https://schema.org/accessModeSufficient)

Although schema.org contains many other properties that describe the accessibility of objects in its taxonomy, these specific properties were developed together as part of a project to improve the discoverability of accessible resources headed by Benetech and IMS Global. Many of these properties were derived directly from the [IMS Global AccessForAll (AfA) Information Model Data Element Specification](http://www.imsglobal.org/accessibility/afav3p0pd/AfA3p0_DESinfoModel_v1p0pd.html).

Part of this work included defining vocabularies of recommended values for use with these properties to ensure predictability for machine processing. This document represents those vocabularies.

By defining these vocabularies, not only is it simpler for authors to understand and apply the properties, but it ensures that search tools, user agents and other machine intelligence can easily parse and inform users of the information.

Note

The vocabulary defined in this document is a continuation of the work that was informally hosted on the [WebSchemas wiki](https://www.w3.org/wiki/WebSchemas/Accessibility) (sometimes referred to as the "version 2.0 accessibility properties"). The project was moved to a W3C Community Group to better formalize the document and increase the transparency of its update process.

For more information about the original project, refer to the [Accessibility Metadata Project's web site](http://www.a11ymetadata.org/).

Note

For more information on how to use schema.org accessibility properties not covered by this vocabulary, please refer to their relevant definitions in schema.org.

### 1.2 Vocabulary naming convention

The values defined in this vocabulary follow a camel casing convention: single words are lowercase, while compound words are concatenated into a single value with a capital letter indicating the start of each connected word (e.g., "alternativeText"). This convention is not applied to acronyms, accessibility APIs, and other values that already have recognized naming conventions (e.g., "MathML" and "iOSAccessibility").

Hyphens are used to add additional descriptors to the end of terms. These descriptors are only added to clarify certain ambiguities with terms and only one descriptor is allowed at the end of any given term. For example, languages like MathML and latex are typically associated with encoding math content but are sometimes used to encode chemical equations and formulas. To ensure users can differentiate when these languages are being used for chemistry, the "-chemistry" descriptor is defined in this vocabulary for use on the respective math terms.

To ensure maximum interoperability with user agents that process these properties, use the values exactly as they are defined in this vocabulary. Alternative case spellings may not be recognized (e.g., "mathml" or "aria").

If a user agent does not recognize a term with a descriptor, it should remove the hyphenated descriptor and attempt to process the base term.

User agent developers should be aware that these values may not be strictly validated depending on the context in which they are created and used. Two values that differ only in case should be treated as identical.

### 1.3 Extending the vocabulary

To extend terms with more information, this vocabulary used to recommend the old [slash extension syntax](https://schema.org/docs/old_extension.html) employed by Schema.org until 2015. In this model, extensions of a term are made by adding a slash followed by a refinement term.

Authors are no longer recommended to use this extension mechanism, although the use of slashes is not formally deprecated for backwards compatibility with existing content. The slash syntax was poorly defined, especially when multiple refinements could be specified, making it difficult for machines to process.

When a user may require more information about the characteristics of a resource (e.g., the specifics of what type of braille it contains), it is better to explain these in human-readable terms in an accessibility summary.

If a term in this vocabulary is not be expressive enough, it is now recommended to open an [issue in the tracker](https://github.com/w3c/a11y-discov-vocab/issues) to consider how to improve the existing term (e.g., by renaming terms or defining more specialized cases).

Note

Descriptors are not a general extensibility mechanism. If a term can benefit from a new descriptor, the resulting combined value must be registered in the vocabulary.

### 1.4 Versioning

As this vocabulary was initially developed in a web schemas wiki hosted by W3C, for a long time it did not have a version attached to it. To improve reader awareness of when changes to the document occur, a version was added in early 2026.

Given the history of the document, all updates prior to the first versioned release are considered part of a "1.0" version of the vocabulary. The first versioned document was therefore assigned the value "1.1" and all subsequent releases will increment these numbers as follows:

- The major number will change whenever new terms are added or existing terms are deprecated.

- The minor number will change whenever minor definition clarifications or fixes are made.

## 2. The accessibilityAPI property

### 2.1 Application

Indicates that the resource is compatible with the referenced accessibility API.

Compatibility with an accessibility API indicates that assistive technologies on the platform should be able to access the resource.

The property is not applicable to resources that are not tightly integrated with their user interface. It can describe whether a word processing document that only opens in a specific application will work on a given platform, for example, but is not a useful indicator of whether an HTML document will, as there are numerous user agents a user could use to render it.

Setting the property means that the resource is compatible with the given API(s). It does not necessarily mean that the content will be fully accessible to any given user group.

The expected value of the accessibilityAPI property is a list of the compatible APIs. For metadata formats incapable of expressing lists, the property should be repeated for each API.

Example 1: AccessibilityAPI expressed in JSON-LD

The following example shows the metadata used to express that a word processing document is compatible with AndroidAccessibility and iOSAccessibility platform APIs.

```
{
   "@context": "schema.org",
   "@type": "DigitalDocument",
   …
   "accessibilityAPI": ["AndroidAcessibility",
                        "iOSAccessibility"],
   …
}
```

```
AccessibilityAPI is not applicable to EPUB content.
Interoperability with platform APIs is an issue for Reading Systems
```

```
<div
    vocab="https://schema.org"
    typeof="DigitalDocument">
   …
   <p>
      This word processing document is compatible
      with the
      <span
          property="accessibilityAPI">
         AndroidAccessibility
      </span>
      and
      <span
          property="accessibilityAPI">
         iOSAccessibility
      </span>
      accessibility APIS.
   </p>
   …
</div>
```

```
<div
    itemtype="DigitalDocument"
    itemscope="">
   …
   <p>
      This word processing document is compatible
      with the
      <span
          itemprop="accessibilityAPI">
         AndroidAccessibility
      </span>
      and
      <span
          itemprop="accessibilityAPI">
         iOSAccessibility
      </span>
      APIS.
   </p>
   …
</div>
```

### 2.2 Vocabulary

#### 2.2.1 AndroidAccessibility

Indicates the resource is compatible with the [Android Access API](https://developer.android.com/reference/android/view/accessibility/package-summary.html).

#### 2.2.2 ARIA (deprecated)

Indicates the resource uses [ARIA](https://www.w3.org/TR/wai-aria/) [wai-aria] markup to improve interoperability with platform APIs.

Note

The use of the ARIA value is now deprecated as ARIA is not an accessibility API. The accessibilityFeature property value "ARIA" is now recommended to use to indicate that a resource makes use of ARIA to improve structural navigation.

#### 2.2.3 ATK

Indicates the resource is compatible with the [Accessibility Toolkit (ATK) API](https://gitlab.gnome.org/Archive/atk) [atk] for GNOME.

#### 2.2.4 AT-SPI

Indicates the resource is compatible with the [Assistive Technology Service Provider Interface (AT-SPI) API](https://gitlab.gnome.org/GNOME/at-spi2-core) [at-spi] for GNOME.

#### 2.2.5 BlackberryAccessibility (obsolete)

Indicates the resource is compatible with the [BlackBerry Accessibility API](https://blackberry.com/developers/docs/7.1.0api/net/rim/device/api/ui/accessibility/package-summary.html).

This value is now obsolete as BlackBerry devices phones and operating systems are no longer developed, sold, or maintained.

Note

After 2016, the BlackBerry name was licensed for phones released using the Android platform. Compatibility with these devices must be indicated using the AndroidAccessibility value.

#### 2.2.6 FuchsiaAccessibility

Indicates the resource is compatible with the [Fuchsia Accessibility Framework](https://fuchsia.dev/fuchsia-src/concepts/accessibility/accessibility_framework).

#### 2.2.7 iAccessible2

Indicates the resource is compatible with the [iAccessible2 API](https://wiki.linuxfoundation.org/accessibility/iaccessible2/) [iaccessible2] for Windows.

#### 2.2.8 iOSAccessibility (deprecated)

Authors should use the NSAccessibility value instead.

#### 2.2.9 JavaAccessibility

Indicates the resource is compatible with the [Java Accessibility API](https://www.oracle.com/java/technologies/javase/desktop-accessibility.html) [japi].

#### 2.2.10 MacOSXAccessibility (deprecated)

Authors should use the UIAccessibility value instead.

#### 2.2.11 MSAA

Indicates the resource is compatible with the [Microsoft Active Accessibility (MSAA) API](https://docs.microsoft.com/en-us/dotnet/framework/ui-automation/ui-automation-and-microsoft-active-accessibility) [msaa] for Windows.

#### 2.2.12 NSAccessibility

Indicates the resource is compatible with the [NSAccessibility API](https://developer.apple.com/documentation/appkit/nsaccessibility) for Apple iOS and tvOS applications built on UIKit.

#### 2.2.13 UIAccessibility

Indicates the resource is compatible with the [UIAccessibility API](https://developer.apple.com/documentation/objectivec/nsobject/uiaccessibility) for macOS applications built on AppKit.

#### 2.2.14 UIAutomation

Indicates the resource is compatible with the [User Interface Automation API](https://docs.microsoft.com/en-us/dotnet/framework/ui-automation/ui-automation-and-microsoft-active-accessibility) for Windows.

## 3. The accessibilityControl property

### 3.1 Application

Identifies one or more input methods that allow access to all of the application functionality.

The accessibilityControl property is used to describe the ability of users to interact with the user interface controls that applications provide.

The property is not applicable to resources that are not tightly integrated with their user interface. It can describe whether users can control a word processing document that only opens in a specific application, for example, but is not a useful indicator of whether users can control an HTML document, as there are numerous user agent and assistive technology pairings a user could use to access it.

Setting the property means that the specified control method(s) are compatible with the resource.

The expected value of the accessibilityControl property is a list of the applicable control methods. For metadata formats incapable of expressing lists, the property should be repeated for each control method.

Example 2: accessibilityControl expressed in JSON-LD

The following example shows the metadata for a publication with interactive games that can be controlled by keyboard and mouse input.

```
{
   "@context": "schema.org",
   "@type": "CreativeWork",
   …
   "accessibilityControl": ["fullKeyboardControl",
                            "fullMouseControl"],
   …
}
```

```
<package …>
   <metadata>
      …
      <meta
          property="schema:accessibilityControl">
         fullKeyboardControl
      </meta>
      <meta
          property="schema:accessibilityControl">
         fullMouseControl
      </meta>
   	…
   </metadata>
   …
</package>
```

```
<div
    vocab="https://schema.org"
    typeof="CreativeWork">
   …
   <p>
      This word processing document supports
      user interaction via
      <span
          property="accessibilityControl"
          content="fullKeyboardControl">keyboard</span>
      and
      <span
          property="accessibilityControl"
          content="fullMouseControl">mouse</span>
      input.
   </p>
   …
</div>
```

```
<div
    itemtype="https://schema.org/CreativeWork"
    itemscope="">
   …
   <p>
      This word processing document supports
      user interaction via
      <meta
          itemprop="accessibilityControl"
          content="fullKeyboardControl">
      keyboard and
      <meta
          itemprop="accessibilityControl"
          content="fullMouseControl">
      mouse input.
   </p>
   …
</div>
```

### 3.2 Vocabulary

#### 3.2.1 fullKeyboardControl

Users can fully control the resource through keyboard input.

#### 3.2.2 fullMouseControl

Users can fully control the resource through mouse input.

#### 3.2.3 fullSwitchControl

Users can fully control the resource through switch input.

#### 3.2.4 fullTouchControl

Users can fully control the resource through touch input.

#### 3.2.5 fullVideoControl

Users can fully control the resource through video input.

#### 3.2.6 fullVoiceControl

Users can fully control the resource through voice input.

## 4. The accessibilityFeature property

### 4.1 Application

Content features of the resource, such as accessible media, alternatives and supported enhancements for accessibility.

The accessibilityFeature property provides a list of all the applicable accessibility characteristics of the content. It allows a user agent to discover these characteristics without having to parse or interpret the structure of the content.

For ease of reading, this section splits the vocabulary into the following distinct groups:

- Structure and navigation terms identify navigation aids that are provided to simplify moving around within the media, such as the inclusion of a table of contents or an index.

- Adaptation terms identify content features that provide alternate access to a resource. The inclusion of alternative text in an [html] alt attribute is one of the most commonly identifiable augmentation features.

- Rendering control terms identify content rendering features that users have access to or can control. The ability to modify the appearance of the text is one example.

- Specialized markup terms identify that content is encoded using domain-specific grammars like MathML and ChemML that can provide users a richer reading experience.

- Clarity terms identify ways that the content has been enhanced for clearer readability. Audio with minimized background noise is one example, while content formatted for large print reading is another.

- Tactile terms identify content that is formatted for tactile use, such as graphics and objects.

- Internationalization terms identify those accessibility characteristics of the content which are required for internationalization.

The vocabulary also includes the term "none" that authors can set to indicate that the resource does not contain special enhancements. Similarly, the term "unknown" exists as a placeholder for marking content that authors need to review.

The expected value of the accessibilityFeature property is a list of the applicable features. For metadata formats incapable of expressing lists, the property should be repeated for each feature.

Example 3: accessibilityFeature expressed in JSON-LD

The following example shows the metadata for a book that provides alternative text, extended descriptions, and transcripts to make embedded image, audio, and video content more accessible to screen reader users.

```
{
   "@context": "schema.org",
   "@type": "Book",
   …
   "accessibilityFeature": ["tableOfContents",
                            "alternativeText",
                            "longDescription",
                            "transcript"],
   …
}
```

```
<package …>
   <metadata>
      …
      <meta
          property="rdf:type">
         https://schema.org/Book
      </meta>
      <meta
          property="schema:accessibilityFeature">
         tableOfContents
      </meta>
      <meta
          property="schema:accessibilityFeature">
         alternativeText
      </meta>
      <meta
          property="schema:accessibilityFeature">
         longDescription
      </meta>
      <meta
          property="schema:accessibilityFeature">
         transcript
      </meta>
   	…
   </metadata>
   …
</package>
```

```
<div
    vocab="https://schema.org"
    typeof="Book">
   …
   <p>
      Included accessibility features:
   </p>
   <ul>
   	<li
           property="accessibilityFeature"
           content="tableOfContents">
          Table of contents
       </li>
   	<li
           property="accessibilityFeature"
           content="alternativeText">
          Alternative text for images
       </li>
   	<li
           property="accessibilityFeature"
           content="longDescription">
          Extended descriptions for images
       </li>
   	<li
           property="accessibilityFeature"
           content="transcript">
          Transcripts for videos
       </li>
   </ul>
   …
</div>
```

```
<div
    itemtype="https://schema.org/Book"
    itemscope="">
   …
   <p>
      Included accessibility features:
   </p>
   <ul>
   	<li>
   	   <meta
             itemprop="accessibilityFeature"
             content="tableOfContents">
          Table of contents
       </li>
   	<li>
   	   <meta
             itemprop="accessibilityFeature"
             content="alternativeText">
          Alternative text for images
       </li>
   	<li>
   	   <meta
             itemprop="accessibilityFeature"
             content="longDescription">
          Extended descriptions for images
       </li>
   	<li>
   	   <meta
             itemprop="accessibilityFeature"
             content="transcript">
          Transcripts for videos
       </li>
   </ul>
   …
</div>
```

### 4.2 Vocabulary

#### 4.2.1 Structure and navigation terms

The structure and navigation term identify structuring and navigation aids that facilitate use of a resource.

##### 4.2.1.1 annotations (deprecated)

The resource includes annotations from the author, instructor and/or others.

Note

The use of the annotations value is now deprecated due to the general nature of annotations in published works. When authors or publishers add annotations to a work, they provide information for all readers; they are not used as a means of enhancing otherwise inaccessible content.

##### 4.2.1.2 ARIA

Indicates the resource includes ARIA roles to organize and improve the structure and navigation.

The use of this value corresponds to the inclusion of [Document Structure](https://www.w3.org/TR/wai-aria/#document_structure_roles), [Landmark](https://www.w3.org/TR/wai-aria/#landmark_roles), [Live Region](https://www.w3.org/TR/wai-aria/#live_region_roles), and [Window](https://www.w3.org/TR/wai-aria/#window_roles) roles [wai-aria].

Note

The accessibilityControl property can be used to indicate what input devices custom controls are accessible with.

##### 4.2.1.3 bookmarks (deprecated)

The work includes bookmarks to facilitate navigation to key points.

Note

The use of the bookmarks value is now deprecated due to its ambiguity. For PDF bookmarks, the tableOfContents value should be used instead.

##### 4.2.1.4 index

The resource includes an index to the content.

##### 4.2.1.5 pageBreakMarkers

(Formerly printPageNumbers.)

The resource includes static page markers, such as those identified by the [doc-pagebreak role](https://www.w3.org/TR/dpub-aria/#doc-pagebreak) [dpub-aria].

This value is most commonly used with ebooks for which there is a statically paginated equivalent, such as a print edition, but it is not required that the page markers correspond to another work. The markers may exist solely to facilitate navigation in purely digital works.

Note

The value printPageNumbers is considered a synonym of pageBreakMarkers. Although its use is not formally deprecated, authors are strongly encouraged to use the more general pageBreakMarkers. Whether the markers correspond to a statically paginated alternative can be indicated through other metadata, such as a dc:source declaration.

##### 4.2.1.6 pageNavigation

The resource includes a means of navigating to static page break locations.

The most common way of providing page navigation in digital publications is through a page list. The EPUB [page-list navigation feature](https://www.w3.org/TR/epub/#sec-nav-pagelist) [epub-3] and the [pagelist](https://www.w3.org/TR/dpub-aria/#doc-pagelist) role [dpub-aria] are two examples.

##### 4.2.1.7 readingOrder

The ordering of the content in the markup matches its visual presentation, as described in [success criterion 1.3.2 (Meaningful Sequence)](https://www.w3.org/TR/WCAG2/#meaningful-sequence) [wcag2]. For example, CSS styling is not used to position content visually in a different order from the markup.

##### 4.2.1.8 structuralNavigation

The use of headings in the resource fully and accurately reflects the document hierarchy, allowing navigation by assistive technologies.

##### 4.2.1.9 tableOfContents

The resource includes a table of contents that provides links to the major sections of the content.

##### 4.2.1.10 taggedPDF

The contents of the PDF have been tagged to permit access by assistive technologies.

Only set this value for PDFs whose tagging conforms to the PDF/UA standard [iso-14289-1] [iso-14289-2].

Note

For more information about PDF tagging best practices, refer to [Well-Tagged PDF (WTPDF)](https://pdfa.org/wtpdf/).

#### 4.2.2 Adaptation terms

The adaptation terms identify provisions in the content that enable reading in alternative access modes.

##### 4.2.2.1 alternativeText

Alternative text is provided for visual content (e.g., via the [html] [alt attribute](https://html.spec.whatwg.org/multipage/embedded-content.html#attr-img-alt)).

##### 4.2.2.2 audioDescription

Audio descriptions are available (e.g., via an [html] [track](https://html.spec.whatwg.org/multipage/media.html#the-track-element) element with its kind attribute set to "descriptions").

##### 4.2.2.3 captions (deprecated)

Indicates that synchronized captions are available for audio and video content.

Note

The use of the captions value is now deprecated. Authors should use the more specific closedCaptions or openCaptions values, as appropriate.

##### 4.2.2.4 closedCaptions

Indicates that synchronized closed captions are available for audio and video content.

Closed captions are defined separately from the video, allowing users to control whether they are rendered or not, unlike open captions.

##### 4.2.2.5 describedMath

For use with legacy content that includes math as images only but offers a text description for those images. Also use the accessibilityFeature's of alternativeText and/or longDescription as appropriate.

##### 4.2.2.6 longDescription

Descriptions are provided for image-based visual content and/or complex structures such as tables, mathematics, diagrams, and charts.

Note

Authors may set this property independent of the method they use to provide the extended descriptions (i.e., it is not required to use the obsolete [html] [longdesc attribute](https://html.spec.whatwg.org/multipage/obsolete.html#attr-img-longdesc)).

##### 4.2.2.7 openCaptions

Indicates that synchronized open captions are available for audio and video content.

Open captions are part of the video stream and cannot be turned off by the user, unlike closed captions.

##### 4.2.2.8 signLanguage

Sign language interpretation is available for audio and video content.

Note

Information about the sign language code used should be provided in the accessibility summary.

##### 4.2.2.9 transcript

Indicates that a transcript of the audio content is available.

#### 4.2.3 Rendering control terms

The rendering control values identify that access to a resource and rendering and playback of its content can be controlled for easier reading.

##### 4.2.3.1 displayTransformability

Indicates that the display properties of the content are controllable by the user.

When setting this property, the author must ensure that the following are modifiable (when applicable to their language and writing mode):

- the text foreground and background colors

- the font family and size

- the paragraph spacing

- the text margin

- the line height

- the letter and word spacing

- the text alignment

- the writing direction (horizontal or vertical)

- the display of ruby (both visibility and text color)

- the inclusion of space characters as word separators

Note

The preceding list may not capture all needed display transformability characteristics for all languages. In such cases, authors must ensure the missing characteristics are also transformable when setting this metadata. To request an addition to the list, please open an issue in [the vocabulary tracker](https://github.com/w3c/a11y-discov-vocab/issues).

In addition, text must not be represented as images unless it falls under the exceptions of [success criterion 1.4.5 (Images of Text)](https://www.w3.org/TR/WCAG2/#images-of-text) [wcag2].

Note that setting this property does not mean that users will be able to control all the properties of the display in all user agents. It only indicates that the author has not limited the ability of users to change the settings (e.g., by using style attributes [html] or !important declarations [css-cascade-4] that prevent user agents from altering the properties, or by restricting users from modifying Word or PDF files).

The property must not be set for content for which no user agents are available that can transform the appearance and presentation of the text.

##### 4.2.3.2 synchronizedAudioText

Describes a resource that offers both audio and text, with information that allows them to be rendered simultaneously. The granularity of the synchronization is not specified. This term is not recommended when the only material that is synchronized is the document headings.

##### 4.2.3.3 timingControl

For content with timed interaction, this value indicates that the user can control the timing to meet their needs (e.g., pause and reset)

##### 4.2.3.4 unlocked

No digital rights management or other content restriction protocols have been applied to the resource.

#### 4.2.4 Specialized markup terms

The specialized markup terms identify content available in specialized markup grammars. These grammars typically provide users with enhanced structure and navigation capabilities.

##### 4.2.4.1 ChemML

Identifies that chemical information is encoded using the [ChemML markup language](https://hachmannlab.github.io/chemml/).

##### 4.2.4.2 latex

Identifies that mathematical equations and formulas are encoded in the [LaTeX typesetting system](https://www.latex-project.org/).

##### 4.2.4.3 latex-chemistry

Identifies that the [LaTeX typesetting system](https://www.latex-project.org/) is used to encode chemical equations and formulas.

##### 4.2.4.4 MathML

Identifies that mathematical equations and formulas are encoded in MathML [mathml3].

##### 4.2.4.5 MathML-chemistry

Identifies that MathML [mathml3] is used to encode chemical equations and formulas.

##### 4.2.4.6 ttsMarkup

One or more of [ssml], [pronunciation-lexicon], and [css-speech] properties has been used to enhance text-to-speech playback quality.

#### 4.2.5 Clarity terms

The clarity terms identify ways that the content has been enhanced for improved auditory or visual clarity.

##### 4.2.5.1 highContrastAudio

Audio content with speech in the foreground meets the contrast thresholds set out in [success criterion 1.4.7 (Low or No Background Audio)](https://www.w3.org/TR/WCAG2/#low-or-no-background-audio) [wcag2].

Note

Information about the how the audio meets the requirement should be provided in the accessibility summary (i.e., there is no background noise, at least 20db difference between foreground speech and background noise, or the background noise can be turned off.)

##### 4.2.5.2 highContrastDisplay

Content meets the visual contrast threshold set out in [success criterion 1.4.6 (Contrast (Enhanced))](https://www.w3.org/TR/WCAG2/#contrast-enhanced) [wcag2].

##### 4.2.5.3 largePrint

The content has been formatted to meet large print guidelines.

The property is not set if the font size can be increased. See displayTransformability.

Note

Information about the type of large print (e.g., the font size) should be provided in the accessibility summary.

#### 4.2.6 Tactile terms

The tactile terms identify content that is available in tactile form.

##### 4.2.6.1 braille

Alternatives are available in braille.

Note

Information about the type of braille (e.g., ASCII, unicode, nemeth), whether the braille is contracted or not, and what code the braille conforms to should be provided in the accessibility summary.

##### 4.2.6.2 tactileGraphic

When used with creative works such as books, indicates that the resource includes tactile graphics.

When used to describe an image resource or physical object, indicates that the resource is a tactile graphic.

Note

Refer to the [BANA Guidelines and Standards for Tactile Graphics](http://www.brailleauthority.org/tg/) for more information about tactile graphic formats and formatting.

##### 4.2.6.3 tactileObject

When used with creative works such as books, indicates that the resource includes models to generate tactile 3D objects.

When used to describe a physical object, indicates that the resource is a tactile 3D object.

#### 4.2.7 Internationalization terms

The internationalization terms identify those accessibility characteristics of the content which are required for internationalization.

##### 4.2.7.1 fullRubyAnnotations

Indicates that [ruby annotations](https://www.w3.org/TR/jlreq/#usage_of_ruby) [jlreq] are attached to every CJK ideographic character in the content. Ruby annotations are used as pronunciation guides for the logographic characters for languages like Chinese or Japanese. They make difficult CJK ideographic characters more accessible.

If some but not all CJK ideographic characters have ruby annotations, use the rubyAnnotations value.

##### 4.2.7.2 horizontalWriting

Indicates that the content can be laid out horizontally (e.g, using the horizontal-tb writing mode of [css-writing-modes-3]). This value should only be set when the language of the content allows both horizontal and vertical directions. Notable examples of such languages are Chinese, Japanese, and Korean.

Note

Some dyslexic Japanese can read horizontal writing but cannot read vertical writing.

##### 4.2.7.3 rubyAnnotations

Indicates that [ruby annotations](https://www.w3.org/TR/jlreq/#usage_of_ruby) are attached to some but not all CJK ideographic characters in the content.

If all CJK ideographic characters have ruby annotations, use the fullRubyAnnotations value.

##### 4.2.7.4 verticalWriting

Indicates that the content can be laid out vertically (e.g, using the vertical-rl of [css-writing-modes-3]). This value should only be set when the language of the content allows both horizontal and vertical directions.

##### 4.2.7.5 withAdditionalWordSegmentation

Indicates that the content can be rendered with additional word segmentation.

Note

Although the space character is not typically used for word segmentation in languages such as Chinese, Japanese, Thai and Lao, it may be used for accessibility reasons.

##### 4.2.7.6 withoutAdditionalWordSegmentation

Indicates that the content can be rendered without additional word segmentation.

#### 4.2.8 none

Indicates that the resource does not contain any accessibility features.

The none value must not be set with any other feature value.

#### 4.2.9 unknown

Indicates that the author has not yet checked if the resource contains accessibility features. This value is only intended as a placeholder until an accessibility review can be completed.

The unknown value must not be set with any other feature value.

## 5. The accessibilityHazard property

### 5.1 Application

A characteristic of the described resource that is physiologically dangerous to some users. Related to [WCAG 2.0 guideline 2.3](https://www.w3.org/TR/WCAG2/#seizures-and-physical-reactions).

Identifying potential hazards that a resource poses allows users to determine if a resource poses a risk to them and to potentially filter out content that could be harmful.

The expected value of the accessibilityHazard property is a list of the applicable hazards. For metadata formats incapable of expressing lists, the property should be repeated for each hazard.

The accessibilityHazard property currently allows three types of hazards to be identified: flashing, motion simulation, and sound. These correspond to the values flashing, motionSimulation, and sound.

It also allows authors to indicate that each of the hazards is not present. In this case, the values follow the pattern "no…Hazard", using the hazard names in place of the ellipsis (e.g., noFlashingHazard).

If the author is sure there are no hazards, they are recommended to use the value "none" in place of specifying that each individual hazard is not present. When setting this value, no other hazard statuses are allowed.

Authors can additionally indicate that they are unable to determine if a hazard is present. In this case, the values follow the pattern "unknown…Hazard", using the hazard names in place of the ellipsis (e.g., unknownSoundHazard).

Authors can set the value unknown if they are unsure whether any hazards are present (e.g., because they do not know how, or are unable, to assess them). When setting this value, no other hazard statuses are allowed.

Example 4: Mix of accessibility hazard expressed in JSON-LD

This example shows the metadata for a web page that embeds a video game with flashing hazard, but without any sound or motion simulation.

```
{
   "@context": "schema.org",
   "@type": "WebPage",
   …
   "accessibilityHazard": ["flashingHazard",
                           "noMotionSimulationHazard",
                           "noSoundHazard"],
   …
}
```

```
Not applicable
```

```
<div
    vocab="https://schema.org"
    typeof="WebPage">
   …
   <p>
      This page contains video with
      <span
          property="accessibilityHazard">
         flashing
      </span>
      sequences that may affect photosensitive
      readers. There are no known
      <span property="accessibilityHazard"
            content="noMotionSimulationHazard">
      motion simulation</span> or
      <span property="accessibilityHazard"
            content="noSoundHazard">sound<span>
      hazards.
   </p>
   …
</div>
```

```
<div
    itemtype="https://schema.org/WebPage"
    itemscope="">
   …
   <p>
      This page contains video with
      <span
          itemprop="accessibilityHazard">
         flashing
      </span>
      sequences that may affect photosensitive
      readers. There are no known
      <span itemprop="accessibilityHazard"
            content="noMotionSimulationHazard">
      motion simulation</span> or
      <span itemprop="accessibilityHazard"
            content="noSoundHazard">sound<span>
      hazards.
   </p>
   …
</div>
```

Example 5: Unknown accessibility hazard expressed in JSON-LD

This example shows the metadata for a textbook that has no content that moves or flashes, but the author is uncertain if the embedded audio clips could present a hazard.

```
{
   "@context": "schema.org",
   "@type": "Book",
   …
   "accessibilityHazard": ["noFlashingHazard",
                           "noMotionSimulationHazard",
                           "unknownSoundHazard"],
   …
}
```

```
<package …>
   <metadata>
      …
      <meta
          property="schema:accessibilityHazard">
         noFlashingHazard
      </meta>
      <meta
          property="schema:accessibilityHazard">
         noMotionSimulationHazard
      </meta>
      <meta
          property="schema:accessibilityHazard">
         unknownSoundHazard
      </meta>
  	…
   </metadata>
   …
</package>
```

```
<div
    vocab="https://schema.org"
    typeof="Book">
   …
   <p>
      This textbook does not have
      <span property="accessibilityHazard"
            content="noMotionSimulationHazard">
      motion simulation</span> or
      <span property="accessibilityHazard"
         content="noFlashingHazard">flashing<span>
      hazards, but it is unknown if there is
      a <span property="accessibilityHazard"
         content="unknownSoundHazard">sound</span>
       hazard.
   </p>
   …
</div>
```

```
<div
    itemtype="https://schema.org/Book"
    itemscope="">
   …
   <p>
      This textbook does not have
      <span
          itemprop="accessibilityHazard"
          content="noMotionSimulationHazard">
         motion simulation
      </span> or
      <span
          itemprop="accessibilityHazard"
          content="noFlashingHazard">
         flashing
      </span>
      hazards, but it is unknown if there is a
      <span itemprop="accessibilityHazard"
         content="unknownSoundHazard">
      sound</span> hazard.
   </p>
   …
</div>
```

Example 6: No accessibility hazards expressed in JSON-LD

The following example shows the metadata for a novel written entirely in text so it has no hazards.

```
{
   "@context": "schema.org",
   "@type": "Book",
   …
   "accessibilityHazard": ["none"],
   …
}
```

```
<package …>
   <metadata>
      …
      <meta
          property="schema:accessibilityHazard">
         none
      </meta>
  	…
   </metadata>
   …
</package>
```

```
<div
    vocab="https://schema.org"
    typeof="Book">
   …
   <p>
      This book has <span
          property="accessibilityHazard"
          content="none">
         no hazards
      </span>.
   </p>
   …
</div>
```

```
<div
    itemtype="https://schema.org/Book"
    itemscope="">
   …
   <p>
      This book has
      <span
          itemprop="accessibilityHazard"
          content="none">
         no hazards
      </span>.
   </p>
   …
</div>
```

### 5.2 Vocabulary

#### 5.2.1 Hazard terms

##### 5.2.1.1 flashing

Indicates that the resource presents a flashing hazard for photosensitive persons.

This value should be set when the content meets the hazard thresholds described in [success criterion 2.3.1 (Three Flashes or Below Threshold)](https://www.w3.org/TR/WCAG2/#three-flashes-or-below-threshold) [wcag2].

The flashing value must not be set when any of the noFlashingHazard, unknownFlashingHazard, none, or unknown values is set.

##### 5.2.1.2 motionSimulation

Indicates that the resource contains instances of motion simulation that may affect some individuals.

Some examples of motion simulation include video games with a first-person perspective and CSS-controlled backgrounds that move when a user scrolls a page.

The motionSimulation value must not be set when any of the noMotionSimulationHazard, unknownMotionSimulationHazard, none, or unknown values is set.

##### 5.2.1.3 sound

Indicates that the resource contains auditory sounds that may affect some individuals.

Editor's note

The application of this value is currently under discussion as its application is underspecified.

The sound value must not be set when any of the noSoundHazard, unknownSoundHazard, none, or unknown values are set.

#### 5.2.2 No hazard terms

##### 5.2.2.1 none

Indicates that the resource does not contain any hazards.

It is recommended to use the none value when there are no hazards instead of individual statements for noSoundHazard, noMotionSimulationHazard, and noFlashingHazard.

The none value must not be set when specifying either a known hazard or the unknown value. It should not be set when negative hazard claims are made.

##### 5.2.2.2 noFlashingHazard

Indicates that the resource does not present a flashing hazard.

The noFlashingHazard value must not be set when any of the flashing, unknownFlashing, or unknown values is set.

It should not be set when the none value is set.

##### 5.2.2.3 noMotionSimulationHazard

Indicates that the resource does not contain instances of motion simulation.

The noMotionSimulation value must not be set when any of the motionSimulation, unknownMotionSimulationHazard, or unknown values is set.

It should not be set when the none value is set.

##### 5.2.2.4 noSoundHazard

Indicates that the resource does not contain auditory hazards.

Editor's note

The application of this value is currently under discussion as its application is underspecified.

The noSoundHazard value must not be set when either of the sound, unknownSoundHazard, or unknown values is set.

It should not be set when the none value is set.

#### 5.2.3 Unknown hazard terms

##### 5.2.3.1 unknown

Indicates that the author is not able to determine if the resource presents any hazards.

It is recommended to use the unknown value when all hazards are unknown instead of individual statements for unknownSoundHazard, unknownMotionSimulationHazard, and unknownFlashingHazard.

The unknown value must not be set when specifying either a known hazard or the none value. It should not be set with the individual unknown hazard value.

##### 5.2.3.2 unknownFlashingHazard

Indicates that the author cannot determine if a flashing hazard exists.

The unknownFlashingHazard value must not be set when any of the flashing, noFlashingHazard, none values is set.

It should not be set when the unknown value is set.

##### 5.2.3.3 unknownMotionSimulationHazard

Indicates that it is unknown if a motion simulation hazard exists within the content.

The unknownMotionSimulation value must not be set when any of the motionSimulation, noMotionSimulationHazard or none values is set.

It should not be set when the unknown value is set.

##### 5.2.3.4 unknownSoundHazard

Indicates that it is unknown if an auditory hazard exists within the content.

The unknownSoundHazard value must not be set when either of the sound, unknownSoundHazard, or unknown values is set.

It should not be set when the none value is set.

## 6. The accessibilitySummary property

A human-readable summary of specific accessibility features or deficiencies, consistent with the other accessibility metadata but expressing subtleties such as "short descriptions are present but long descriptions will be needed for non-visual users" or "short descriptions are present and no long descriptions are needed."

The accessibilitySummary property is a free-form field that allows authors to describe the accessible properties of the resource. As a result, it does not have an associated vocabulary.

Example 7: accessibilitySummary expressed in JSON-LD

The following example shows a basic accessibility summary that indicates a book meets WCAG 2.1 Level AA.

```
{
   "@context": "schema.org",
   "@type": "Book",
   …
   "accessibilitySummary": "This publication meets WCAG 2.1 Level AA.",
   …
}
```

```
<package …>
   <metadata>
      …
      <meta
          property="rdf:type">
         Book
      </meta>
      <meta
          property="schema:accessibilitySummary">
         This publication meets the
         requirements of WCAG 2.1 Level AA.
      </meta>
   	…
   </metadata>
   …
</package>
```

```
<div
    vocab="https://schema.org"
    typeof="Book">
   …
   <dl>
      …
      <dt>Accessibility Summary:</dt>
      <dd> 
         <p property="accessibilitySummary">This
            publication meets the requirements of
            WCAG 2.1 Level AA.</p>
      </dd>
   </dl>
   …
</div>
```

```
<div
    itemtype="https://schema.org/Book"
    itemscope="">
   …
   <dl>
      …
      <dt>Accessibility Summary:</dt>
      <dd> 
         <p itemprop="accessibilitySummary">This 
            publication meets the requirements of
            WCAG 2.1 Level AA …</p>
      </dd>
   </dl>
   …
</div>
```

## 7. The accessMode property

### 7.1 Application

The human sensory perceptual system or cognitive faculty through which a person may process or perceive the intellectual content of a resource, not including any adaptations of the content (e.g., text alternatives for images).

The accessMode property describes the ways information is encoded in the resource, where information is defined as any content that contributes to the understanding of the resource.

The expected value of the accessMode property is a list of the applicable access modes. For metadata formats incapable of expressing lists, the property should be repeated for each access mode.

Note

The access modes do not tell users if all the specified modes are necessary to consume the information or if only individual modes or combinations are necessary (e.g., in a book with audio content, the ability to read textual content may be sufficient if transcripts are provided).

The accessModeSufficient property is designed to fill this gap of understanding the combinations of modes necessary to fully consume the information.

Example 8: accessMode expressed in JSON-LD

The following example shows the metadata for a publication that contains both text and images.

```
{
   "@context": "schema.org",
   "@type": "CreativeWork",
   …
   "accessMode": ["textual",
                  "visual"],
   …
}
```

```
<package …>
   <metadata>
      …
      <meta
          property="schema:accessMode">
         textual
      </meta>
      <meta
          property="schema:accessMode">
         visual
      </meta>
   	…
   </metadata>
   …
</package>
```

```
<div
    vocab="https://schema.org"
    typeof="CreativeWork">
   …
   <p>
      This book contains both
      <span
          property="accessMode">textual</span>
      and
      <span
          property="accessMode">visual</span>
         content.
   </p>
   …
</div>
```

```
<div
    itemtype="https://schema.org/CreativeWork"
    itemscope="">
   …
   <p>
      This book contains both
      <span
          itemprop="accessMode">textual</span>
      and
      <span
          itemprop="accessMode">visual</span>
         content.
   </p>
   …
</div>
```

### 7.2 Vocabulary

#### 7.2.1 auditory

Indicates that the resource contains information encoded in auditory form.

Note

This value is not set when the auditory content conveys no information. For example, an instructional video might include background music while all the necessary information to complete the task is conveyed visually and/or through text captions.

#### 7.2.2 tactile

Indicates that the resource contains information encoded in tactile form.

Note that although an indication of a tactile mode often indicates the content is encoded using a braille system, this is not always the case. Tactile perception may also indicate, for example, the use of tactile graphics to convey information.

#### 7.2.3 textual

Indicates that the resource contains information encoded in textual form.

Note

This value is not set if the only textual content is for navigational purposes. For example, an audiobook might include a table of contents, but it is not necessary to read the table of contents to read the work. Likewise, books with synchronized text-audio playback may only include headings to allow structured navigation.

#### 7.2.4 visual

Indicates that the resource contains information encoded in visual form.

Note

This value is not set if the only visual imagery is presentational or not directly relevant to understanding the content. Examples of this type of imagery include cover images for publications, corporate logos, and purely decorative images.

### 7.3 Visual content indicators

Caution: Although user agents should infer a visual access mode when any of the values defined in this section is set, it is strongly recommended not to rely on this behaviour. Always set the value visual in addition to these indicators.

The visual content indicators are not strictly access modes but combine a visual access mode with information about the nature of the visual content in a publication, such as whether charts, music, or math equations are encoded as images.

Users can then decide whether the content will still meet their needs. For example, if the math equations in a textbook are encoded as images, with only text descriptions to make them accessible, a user might opt to keep searching for an alternative that uses MathML markup.

#### 7.3.1 chartOnVisual

Indicates that the resource contains charts encoded in visual form.

#### 7.3.2 chemOnVisual

Indicates that the resource contains chemical equations encoded in visual form.

#### 7.3.3 colorDependent

Indicates that the resource contains information encoded such that color perception is necessary.

#### 7.3.4 diagramOnVisual

Indicates that the resource contains diagrams encoded in visual form.

#### 7.3.5 mathOnVisual

Indicates that the resource contains mathematical notations encoded in visual form.

#### 7.3.6 musicOnVisual

Indicates that the resource contains musical notation encoded in visual form.

#### 7.3.7 textOnVisual

Indicates that the resource contains text encoded in visual form.

## 8. The accessModeSufficient property

### 8.1 Application

A list of single or combined access modes that are sufficient to understand all the intellectual content of a resource, including any adaptations.

Although the access modes indicate how the information is encoded in its default form, knowing the encoding only describes one possible perceptual pathway through the content. For example, a book with textual and visual content will, at the most basic level, require an individual who can read text and view images.

The author of the content may, however, provide alternatives to a specific access mode that allow the content to be wholly consumed in another manner. The use of alternative text and extended descriptions, for example, can allow a user who cannot perceive visual content to read all the information in textual form (e.g., through text-to-speech playback).

In such a case, a resource with textual and visual access modes could have both a textual and visual sufficient access mode and a purely textual access mode — because there are text equivalents for the visual content. Specifying there is an additional textual-only pathway through the content allows users of screen readers, for example, to recognize that the content will be readable by them.

It is for this reason that content that has multiple access modes may have one or more sets of sufficient access modes: each listing of sufficient access modes provides users with one possible combination of reading modes that allow the content to be read in full.

Although listing the combinations of access modes that allow a user to read all the content is helpful, the most important sufficient access modes to list are the single-value ones. Users looking for an alternative to the default encoding of the content typically are looking for a single presentation mode (e.g., a fully textual pathway to use with a text-to-speech renderer or a fully auditory pathway to listen to).

The expected value of the accessModeSufficient property is an [ItemList](https://schema.org/ItemList). Each entry in the ItemList must be a list of one or more access modes representing one pathway.

For formats incapable of expressing lists, the property should be repeated for each set of sufficient access modes. In these cases, it is recommended to use a comma-separated list of values.

Example 9: accessModeSufficient expressed in JSON-LD

The following metadata shows that a publication has two ways in which the information can be read: one is via the ability to read the text and perceive the images, and the other via text only.

```
{
   "@context": "schema.org",
   "@type": "CreativeWork",
   …
   "accessModeSufficient": [
      {
         "@type": "ItemList",
         "itemListElement": ["textual","visual"],
         "description": "Text and images"
      },
      {
         "@type": "ItemList",
         "itemListElement": ["textual"],
         "description": "Text only"
      }
   ]
   …
}
```

```
<package …>
      …
   <metadata>
      <meta
          property="schema:accessModeSufficient">
         textual,visual
      </meta>
      <meta
          property="schema:accessModeSufficient">
         textual
      </meta>
  	…
   </metadata>
   …
</package>
```

```
<div
    vocab="https://schema.org"
    typeof="CreativeWork">
   …
   <dl>
      …
      <dt>Sufficient Access Modes:</dt>
      <dd property="accessModeSufficient">
         <ul>
            <li>
            	<div typeof="ItemList">
                   <meta property="itemListElement" content="textual">
                   <meta property="itemListElement" content="visual">
                   <span property="description">Text and Images</span>
            	</div>
            </li>
            <li>
            	<div typeof="ItemList">
                   <meta property="itemListElement" content="textual">
                   <span property="description">Text</span>
            	</div>
            </li>
         </ul>
      </dd>
   </dl>
   …
</div>
```

```
<div
    itemtype="https://schema.org/CreativeWork"
    itemscope="">
   …
   <dl>
      …
      <dt>Sufficient Access Modes:</dt>
      <dd itemprop="accessModeSufficient">
         <ul>
            <li>
            	<div itemtype="ItemList" itemscope="">
                   <meta itemprop="itemListElement" content="textual">
                   <meta itemprop="itemListElement" content="visual">
                   <span itemprop="description">Text and Images</span>
            	</div>
            </li>
            <li>
            	<div itemtype="ItemList" itemscope="">
                   <meta itemprop="itemListElement" content="textual">
                   <span itemprop="description">Text</span>
            	</div>
            </li>
         </ul>
      </dd>
   </dl>
   …
</div>
```

### 8.2 Vocabulary

#### 8.2.1 auditory

Indicates that auditory perception is necessary to consume the information.

#### 8.2.2 tactile

Indicates that tactile perception is necessary to consume the information.

#### 8.2.3 textual

Indicates that the ability to read textual content is necessary to consume the information.

Note that reading textual content does not require visual perception, as textual content can be rendered as audio using a text-to-speech capable device or assistive technology.

#### 8.2.4 visual

Indicates that visual perception is necessary to consume the information.

## 9. Examples

### 9.1 Book

The following example shows how accessibility metadata could be used to enhance a library record available on the Web.

```
<div itemscope="" itemtype="http://schema.org/Book">
   <meta itemprop="bookFormat" content="EBook/DAISY3" />
   <meta itemprop="accessibilityFeature" content="ARIA" />
   <meta itemprop="accessibilityFeature" content="largePrint" />
   <meta itemprop="accessibilityFeature" content="highContrastDisplay" />
   <meta itemprop="accessibilityFeature" content="displayTransformability" />
   <meta itemprop="accessibilityFeature" content="longDescription" />
   <meta itemprop="accessibilityFeature" content="alternativeText" />
   <meta itemprop="accessibilityFeature" content="readingOrder" />
   <meta itemprop="accessibilityFeature" content="structuralNavigation" />
   <meta itemprop="accessibilityFeature" content="tableOfContents" />
   <meta itemprop="accessibilityControl" content="fullKeyboardControl" />
   <meta itemprop="accessibilityControl" content="fullMouseControl" />
   <meta itemprop="accessibilityHazard" content="none" />
   <dl>
      <dt>Name:</dt>
      <dd itemprop="name">Holt Physical Science</dd>
      <dt>Brief Synopsis:</dt>
      <dd itemprop="description">NIMAC-sourced textbook</dd>
      <dt>Long Synopsis:</dt>
      <dd>N/A</dd>
      <dt>Book Quality:</dt>
      <dd>Publisher Quality</dd>
      <dt>Book Size:</dt>
      <dd itemprop="numberOfPages">598 Pages</dd>
      <dt>ISBN-13:</dt>
      <dd itemprop="isbn">9780030426599</dd>
      <dt>Publisher:</dt>
      <dd itemprop="publisher" itemtype="http://schema.org/Organization" itemscope="">Holt, Rinehart
         and Winston</dd>
      <dt>Date of Addition:</dt>
      <dd>06/08/10</dd>
      <dt>Copyright Date:</dt>
      <dd itemprop="copyrightYear">2007</dd>
      <dt>Copyrighted By:</dt>
      <dd itemprop="copyrightHolder" itemtype="http://schema.org/Organization" itemscope="">Holt,
         Rinehart and Winston</dd>
      <dt>Adult content:</dt>
      <dd><meta itemprop="isFamilyFriendly" content="true" />No</dd>
      <dt>Language:</dt>
      <dd><meta itemprop="inLanguage" content="en-US" />English US</dd>
      <dt>Essential Images:</dt>
      <dd>861</dd>
      <dt>Described Images:</dt>
      <dd>910</dd>
      <dt>Categories:</dt>
      <dd><span itemprop="genre">Educational Materials</span></dd>
      <dt>Grade Levels:</dt>
      <dd>Sixth grade, Seventh grade, Eighth grade</dd>
      <dt>NIMAC:</dt>
      <dd>This book is currently only available to public K-12 schools and organizations in the United
         States for use with students with an IEP, because it was created from files supplied by the
         NIMAC under these restrictions. Learn more in the NIMAC Support Center.</dd>
   </dl>
   
   <div class="bookReviews" itemprop="aggregateRating" itemscope=""
      itemtype="http://schema.org/AggregateRating">
      <h2>Reviews of Holt Physical Science (<span itemprop="reviewCount">0</span> reviews)</h2>
      <div class="bookReviewScore">
         <span><span itemprop="ratingValue">0</span> - No Rating Yet</span>
      </div>
   </div>
</div>
```

### 9.2 Video

This example shows how the accessibility metadata could be used to augment a record for a video.

```
<dl itemtype="http://schema.org/VideoObject" itemscope="">
   <dt>Title:</dt>
   <dd itemprop="name">Arctic Climate Perspectives</dd>
   <dt>Description:</dt>
   <dd itemprop="description">This video, adapted from material provided by the ECHO
      partners, describes how global climate change is affecting Barrow, Alaska.</dd>
   <dt>Adaptation Type:</dt>
   <dd><span itemprop="accessibilityFeature">captions</span></dd>
   <dt>Access Mode:</dt>
   <dd>auditory, visual</dd>
   <dt>URL:</dt>
   <dd><a itemprop="url" href="http://www.example.org/asset/echo07_vid_climate"
      >http://www.example.org/asset/echo07_vid_climate</a>/</dd>
   <dt>Has Adaptation:</dt>
   <dd>http://www.example.org/asset/echo07_vid_climate_dvs/</dd>
   <dt>Subjects:</dt>
   <dd><span itemprop="about">National K-12 Subject::Science::Earth and Space
      Science::Water Cycle, Weather, and Climate::Structure and Composition of the
      Atmosphere, National K-12 Subject::Science::Earth and Space Science::Water Cycle,
      Weather, and Climate::Climate</span></dd>
   <dt>Education Level:</dt>
   <dd>Grade 6, Grade 7, Grade 8, Grade 9</dd>
   <dt>Audience:</dt>
   <dd><span itemprop="intendedEndUserRole">Learner</span></dd>
   <dt>Resource Type:</dt>
   <dd><span itemprop="genre">Audio/Visual</span>,
      <span itemprop="genre">Movie/Animation</span></dd>
   <dt>Language:</dt>
   <dd><span itemprop="inLanguage">en-US</span></dd>
   <dt>Publication Date:</dt>
   <dd itemprop="datePublished">2007-02-12</dd>
   <dt>Rights:</dt>
   <dd>Download and Share, <a itemprop="useRightsUrl"
      href="http://www.example.org/oerlicense/2/"
      >http://www.example.org/oerlicense/2/</a></dd>
</dl>
```

## A. Change log

Note that this change log only identifies substantive changes to the vocabulary — those that add or deprecate terms, or are similarly noteworthy.

For a list of all issues addressed (typos, minor definition modifications, etc.), refer to the [Community Group's issue tracker](https://github.com/w3c/a11y-discov-vocab/issues?q=is%3Aissue+is%3Aclosed).

Changes made in 2026

- 24-Aug-2026: Added version number to the vocabulary title. Refer to [issue 258](https://github.com/w3c/a11y-discov-vocab/issues/258).

- 28-Apr-2026: Updated the definition of readingOrder to make its relationship to WCAG success criterion 1.3.2 clearer. Refer to [issue 261](https://github.com/w3c/a11y-discov-vocab/issues/261).

- 23-Mar-2026: Updated the cited definitions for accessMode and accessModeSufficient to reflect the changes to schema.org. Refer to [issue 254](https://github.com/w3c/a11y-discov-vocab/issues/254).

Changes made in 2025

- 20-June-2025: Deprecated the use of the annotations value for accessibilityFeature. Refer to [issue 166](https://github.com/w3c/a11y-discov-vocab/issues/166).

Changes made in 2024

- 16-Dec-2024: Clarified that the taggedPDF is only to be set when a PDF meets accepted standards for accessibility. Refer to [issue 40](https://github.com/w3c/a11y-discov-vocab/issues/40).

- 25-Nov-2024: Moved the visual access modes that combine descriptions about the nature of the visual content into a new section and caution that they should always be paired with the value visual. Refer to [issue 2653](https://github.com/w3c/epub-specs/issues/2653) in the EPUB tracker.

- 05-Sept-2024: Clarified when it is appropriate to set the displayTransformability property. Refer to [issue 85](https://github.com/w3c/a11y-discov-vocab/pull/85).

- 27-May-2024: Added a new section on appending descriptors to existing values using hyphens. Also added two descriptors: MathML-chemistry and latex-chemistry. Refer to [issue 106](https://github.com/w3c/a11y-discov-vocab/issues/106).

Changes made in 2023

- 18-July-2023: Added internationalization values for ruby, writing direction, and word segmentation. See issues [2](https://github.com/w3c/a11y-discov-vocab/issues/2), [3](https://github.com/w3c/a11y-discov-vocab/issues/3), and [68](https://github.com/w3c/a11y-discov-vocab/issues/68).

- 18-July-2023: Added individual unknown hazard values. See [issue 92](https://github.com/w3c/a11y-discov-vocab/issues/92).

- 05-May-2023: Added FuchsiaAccessibility to the accessibilityAPI values. See [issue 24](https://github.com/w3c/a11y-discov-vocab/issues/24).

- 05-May-2023: Added closedCaptions and openCaptions to replace the more generic captions value. See [issue 26](https://github.com/w3c/a11y-discov-vocab/issues/26).

- 27-Mar-2023: Added unknown feature for placeholder use. See [issue 17](https://github.com/w3c/a11y-discov-vocab/issues/17).

- 06-Feb-2023: Added pageNavigation feature for indicating that a resource has a page list. See [issue 6](https://github.com/w3c/a11y-discov-vocab/issues/6).

- 06-Feb-2023: Added pageBreakMarkers feature for indicating that a resource includes static page break markers. printPageNumbers is retained as a synonym but no longer recommended for use. See [issue 6](https://github.com/w3c/a11y-discov-vocab/issues/6).

Changes made in 2022

- 10-June-2022: Removed references to using the slash syntax to extend terms and recommend against using the mechanism any more. See [issue 5](https://github.com/w3c/a11y-discov-vocab/issues/5).

- 10-June-2022: Clarify that access modes do not apply to presentational content. See [issue 38](https://github.com/w3c/a11y-discov-vocab/issues/38).

- 10-June-2022: Clarify that single-value sufficient access modes are the most important to list. See [pull request 49](https://github.com/w3c/a11y-discov-vocab/pull/49).

- 10-June-2022: Identify hazard and feature property values that must not be specified together to avoid ambiguity. See [pull request 49](https://github.com/w3c/a11y-discov-vocab/pull/49).

- 10-June-2022: Ensure all properties identify their expected values and describe how to handle less expressive formats like EPUB. See [pull request 49](https://github.com/w3c/a11y-discov-vocab/pull/49).

- 09-June-2022: Deprecated the bookmarks feature due to its ambiguous definition. The tableOfContents and annotations values are recommended in its place. See [issue 5](https://github.com/w3c/a11y-discov-vocab/issues/5).

- 08-June-2022: Marked the BlackberryAccessibility API as obsolete. See [issue 12](https://github.com/w3c/a11y-discov-vocab/issues/12).

- 31-May-2022: Clarify the definition of taggedPDF to indicate it is critical for access to the content not just for improved navigation. See [issue 40](https://github.com/w3c/a11y-discov-vocab/issues/40).

- 07-Feb-2022: Restore the "tableOfContents" value for accessibilityFeature. See [pull request 39](https://github.com/w3c/a11y-discov-vocab/pull/39).

- 04-Feb-2022: The accessibilityAPI value "ARIA" is deprecated. It is replaced by a new "ARIA" value for accessibilityFeature for indicating the use of roles of enhanced structural and landmark navigation. See [issue 4](https://github.com/w3c/a11y-discov-vocab/issues/4).

- 26-Jan-2022: The accessibility features have been restructured to better organize them by purpose. See [issue 10](https://github.com/w3c/a11y-discov-vocab/issues/10).

## B. Acknowledgments

The editors would like to thank the [Accessibility Discoverability Vocabulary for Schema.org Community Group participants](https://www.w3.org/community/a11y-discov-vocab/participants) for their ongoing input and suggestions to improve this vocabulary.

Additional thanks go to the original participants of the [Accessibility Metadata Project](http://www.a11ymetadata.org) for their work bringing the properties and vocabularies to reality.

## C. References

### C.1 Informative references

- [at-spi]

[Assistive Technology Service Provider Interface](https://gnome.pages.gitlab.gnome.org/at-spi2-core/libatspi/). The GNOME Project. URL: <https://gnome.pages.gitlab.gnome.org/at-spi2-core/libatspi/>

- [atk]

[ATK - Accessibility Toolkit](https://developer.gnome.org/atk/stable/). The GNOME Project. URL: <https://developer.gnome.org/atk/stable/>

- [css-cascade-4]

[CSS Cascading and Inheritance Level 4](https://www.w3.org/TR/css-cascade-4/). Elika Etemad; Tab Atkins Jr. W3C. 13 January 2022. W3C Candidate Recommendation. URL: <https://www.w3.org/TR/css-cascade-4/>

- [css-speech]

[CSS Speech Module Level 1](https://www.w3.org/TR/css-speech-1/). Léonie Watson; Elika Etemad. W3C. 14 February 2023. CRD. URL: <https://www.w3.org/TR/css-speech-1/>

- [css-writing-modes-3]

[CSS Writing Modes Level 3](https://www.w3.org/TR/css-writing-modes-3/). Elika Etemad; Koji Ishii. W3C. 10 December 2019. W3C Recommendation. URL: <https://www.w3.org/TR/css-writing-modes-3/>

- [dpub-aria]

[Digital Publishing WAI-ARIA Module](https://www.w3.org/TR/dpub-aria/). W3C. URL: <https://www.w3.org/TR/dpub-aria/>

- [epub-3]

[EPUB 3](https://www.w3.org/TR/epub/). W3C. URL: <https://www.w3.org/TR/epub/>

- [html]

[HTML Standard](https://html.spec.whatwg.org/multipage/). Anne van Kesteren; Domenic Denicola; Dominic Farolino; Ian Hickson; Philip Jägenstedt; Simon Pieters. WHATWG. Living Standard. URL: <https://html.spec.whatwg.org/multipage/>

- [iaccessible2]

[IAccessible2](https://wiki.linuxfoundation.org/accessibility/iaccessible2/). Linux Foundation. URL: <https://wiki.linuxfoundation.org/accessibility/iaccessible2/>

- [iso-14289-1]

[ISO 14289-1:2024 — Document management applications — Electronic document file format enhancement for accessibility Part 1: Use of ISO 32000-1 (PDF/UA-1)](https://www.iso.org/standard/64599.html). ISO. URL: <https://www.iso.org/standard/64599.html>

- [iso-14289-2]

[ISO 14289-2:2024 — Document management applications — Electronic document file format enhancement for accessibility Part 2: Use of ISO 32000-2 (PDF/UA-2)](https://www.iso.org/standard/82278.html). ISO. URL: <https://www.iso.org/standard/82278.html>

- [japi]

[Java Accessibility API](http://www.oracle.com/technetwork/java/javase/tech/index-jsp-140174.html). Oracle. URL: <http://www.oracle.com/technetwork/java/javase/tech/index-jsp-140174.html>

- [jlreq]

[Requirements for Japanese Text Layout 日本語組版処理の要件(日本語版)](https://www.w3.org/TR/jlreq/). Hiroyuki Chiba; Junzaburo Edamoto; Richard Ishida; Seiichi Kato; Tatsuo KOBAYASHI; Toshi Kobayashi; Nathaniel McCully; Felix Sasaki; Atsushi Shimono; Hajime Shiozawa; Fuqiao Xue et al. W3C. 11 August 2020. W3C Working Group Note. URL: <https://www.w3.org/TR/jlreq/>

- [mathml3]

[Mathematical Markup Language (MathML) Version 3.0 2nd Edition](https://www.w3.org/TR/MathML3/). David Carlisle; Patrick D F Ion; Robert R Miner. W3C. 10 April 2014. W3C Recommendation. URL: <https://www.w3.org/TR/MathML3/>

- [msaa]

[Microsoft Active Accessibility (MSAA)](https://docs.microsoft.com/en-us/windows/win32/winauto/microsoft-active-accessibility). Microsoft Corporation. URL: <https://docs.microsoft.com/en-us/windows/win32/winauto/microsoft-active-accessibility>

- [pronunciation-lexicon]

[Pronunciation Lexicon Specification (PLS) Version 1.0](https://www.w3.org/TR/pronunciation-lexicon/). Paolo Baggia. W3C. 14 October 2008. W3C Recommendation. URL: <https://www.w3.org/TR/pronunciation-lexicon/>

- [schema-org]

[Schema.org](https://schema.org/). W3C Schema.org Community Group. W3C. 6.0. URL: <https://schema.org/>

- [ssml]

[Speech Synthesis Markup Language (SSML) Version 1.1](https://www.w3.org/TR/speech-synthesis11/). Daniel Burnett; Zhi Wei Shuang. W3C. 7 September 2010. W3C Recommendation. URL: <https://www.w3.org/TR/speech-synthesis11/>

- [wai-aria]

[Accessible Rich Internet Applications (WAI-ARIA) 1.0](https://www.w3.org/TR/wai-aria/). James Craig; Michael Cooper et al. W3C. 20 March 2014. W3C Recommendation. URL: <https://www.w3.org/TR/wai-aria/>

- [wcag2]

[Web Content Accessibility Guidelines (WCAG) 2](https://www.w3.org/TR/WCAG2/). W3C. URL: <https://www.w3.org/TR/WCAG2/>

↑
