# Changelog


This page details the latest major updates made to Google's crawling documentation.


To get the latest crawling documentation updates delivered to you, add the URL of this
page to your [feed reader](https://en.wikipedia.org/wiki/Comparison_of_feed_aggregators),
or add the feed URL directly:
`https://developers.google.com/crawling/docs/changelog/crawling_docs_updates.rss`.

## November 2026

November 23
:

    ### Documented additional existing crawlers and user-triggered fetchers


    **What**: Updated the crawler and fetcher documentation:

    - Added the following user agents to the [special-case crawlers](https://developers.google.com/crawling/docs/crawlers-fetchers/google-special-case-crawlers.md.txt) documentation: `Google-analytics-postbacks`, `Google-Calendar-Importer`, `GoogleDocs`, `Google-Edu`, `pageburst`, and `PlayStore-Google`.
    - Added the following user agents to the [user-triggered fetchers](https://developers.google.com/crawling/docs/crawlers-fetchers/google-user-triggered-fetchers.md.txt) documentation: `AppEngine-Google`, `Google-Apps-Script`, `Google-Cloud-Tasks`, `GoogleImageProxy`, `Google Web Preview`, and `Chrome-Lighthouse`.
    - Moved [`APIs-Google`](https://developers.google.com/crawling/docs/crawlers-fetchers/apis-user-agent.md.txt) from special-case crawlers to the [user-triggered fetchers](https://developers.google.com/crawling/docs/crawlers-fetchers/google-user-triggered-fetchers.md.txt) documentation, and corrected a typo in its documented user agent string (added the missing semicolon after `APIs-Google`). If you hardcoded the old value in your code, update the string to avoid potential bugs.


    **Why** : These crawlers and fetchers are not new; we're documenting existing high-volume
    clients that are more likely to show up in server logs and that we've received questions
    about. Moving `APIs-Google` reflects that its webhook push requests come from
    the user-triggered fetcher IP ranges and ignore `robots.txt` rules.

November 17
:

    ### Added guidance on allowing `Google-Agent`


    **What** : Published a
    [technical guide](https://developers.google.com/crawling/docs/crawlers-fetchers/allow-google-agent.md.txt) on how to
    ensure that `Google-Agent` has access to your website.


    **Why** : To help publishers that want to enable `Google-Agent` for their
    website.

## October 2026

October 30
:

    ### Updated [common crawlers page](https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers.md.txt#google-extended)
    to mention future AI training control support


    **What** : Added a
    [note](https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers.md.txt#google-extended)
    about Google's intention to support the shared machine-readable training preference signal.


    **Why** : Learn more in our
    [blog post](https://developers.google.com/search/blog/2026/10/ai-training-control.md.txt).

October 23
:

    ### Updated guidance on robots.txt specifications


    **What** : Updated the [how Google interprets the robots.txt specification](https://developers.google.com/crawling/docs/robots-txt/robots-txt-spec.md.txt) to add recommendation for percent-encoding in rule paths.


    **Why**: To synchronize the documentation with the episodes of "The Non-Canonical Cabinet" video series.

October 6
:

    ### Added `Retry-After` HTTP header details to the reduce crawl rate documentation


    **What** : Restructured the emergency crawl rate reduction section and added information and
    examples about the `Retry-After` HTTP header to the
    [Reduce the Google crawl rate](https://developers.google.com/crawling/docs/crawlers-fetchers/reduce-crawl-rate.md.txt)
    documentation.


    **Why** : Support for the `Retry-After` HTTP header is not new (it was already
    documented in
    [Temporarily pause or disable a website](https://developers.google.com/search/docs/crawling-indexing/pause-online-business.md.txt)),
    and adding it directly to the crawl rate reduction guide makes it easier to find and
    understand when urgently reducing crawler traffic.

## September 2026

September 17
:

    ### Generalized the `Mediapartners-Google` crawler documentation


    **What** : Updated the
    [`Mediapartners-Google`](https://developers.google.com/crawling/docs/crawlers-fetchers/google-special-case-crawlers.md.txt#mediapartners-google)
    documentation to clarify that it affects various
    ad-related Google products (not just AdSense), and renamed the section heading from
    AdSense to `Mediapartners-Google`.


    **Why** : Crawling preferences addressed to the `Mediapartners-Google` user
    agent affect multiple ad-related Google products (for example, [Google AdSense](https://support.google.com/adsense/answer/99376)
    and [Google Ad Manager](https://support.google.com/admanager/answer/6023726)).

## July 2026

July 22
:

    ### Polished and clarified the crawl budget guide


    **What** : Polished and clarified the
    [Optimize your crawl budget](https://developers.google.com/crawling/docs/crawl-budget.md.txt) page to improve clarity,
    terminology consistency, and flow.


    **Why** : To make the documentation easier to understand and ensure technical terms
    (like *crawl capacity limit*) are used consistently throughout.

July 16
:

    ### Updating the NotebookLM user agent


    **What** : Updated the NotebookLM user agent to be [`Google-GeminiNotebook`](https://developers.google.com/crawling/docs/crawlers-fetchers/google-user-triggered-fetchers.md.txt#gemini-notebook).
    If you hardcoded the old value in your code, update the string to avoid potential bugs. We
    will continue to support the old value to allow for a smooth transition.


    **Why** : [NotebookLM is now Gemini Notebook](https://blog.google/innovation-and-ai/products/gemini-notebook/notebooklm-gemini-notebook/).

July 14
:

    ### Corrected the user agent string for `Google-InspectionTool` user agent


    **What** : Updated the
    [`Google-InspectionTool`](https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers.md.txt#google-inspection-tool)
    user agent string.


    **Why** : The user agent string for `Google-InspectionTool` mistakenly included
    a semicolon, which didn't match the actual user agent string in production. This is now corrected in
    our documentation.

## May 2026

May 4
:

    ### Adding Web Bot Auth documentation


    **What** : Added documentation on [how to authenticate requests with Web Bot Auth](https://developers.google.com/crawling/docs/crawlers-fetchers/web-bot-auth).


    **Why**: To provide site owners with instructions on how to verify requests with Web Bot
    Auth during the experimental phase, as some Google user agents are now starting
    to use Web Bot Auth.

## March 2026

March 20
:

    ### Added the Google-Agent user agent


    **What** : Added the [Google-Agent user agent](https://developers.google.com/crawling/docs/crawlers-fetchers/google-user-triggered-fetchers.md.txt#google-agent) and added the IP ranges for user triggered
    agents to the documentation on [verifying requests from Google crawlers and fetchers](https://developers.google.com/crawling/docs/crawlers-fetchers/verify-google-requests.md.txt).


    **Why**: The Google-Agent user agent is rolling out over the next few weeks, and will be
    used by Google agents hosted on Google infrastructure to navigate the web and perform actions
    upon user request.

March 3
:

    ### Added an overview page about Google's web crawling


    **What** : Added a new page [about how Google's crawling works](https://developers.google.com/crawling/docs/about-crawling.md.txt).


    **Why**: Based on questions we've received over the years, we've put together a resource
    page with basic educational information about crawling to better highlight various resources
    about crawling that are available to site owners.

## February 2026

February 11
:

    ### Updated the location of Google's IP ranges for common crawlers, special crawlers, and user-triggered fetchers


    **What** : Updated the location of Google's
    [IP ranges for common crawlers, special crawlers, and user-triggered fetchers](https://developers.google.com/crawling/docs/crawlers-fetchers/verify-google-requests.md.txt#automatic)
    to the `/crawling/ipranges` directory. The old location will continue to work for
    the time being, but we recommend updating your links to the new location.


    **Why** : Their previous location in `/search/apis/ipranges` was not the most
    logical place, as these IP ranges are used by many Google products (not just Search).

February 3
:

    ### Added information about the default file size limits for Google's crawlers and fetchers


    **What** : Moved the information about the default file size limits of Google's crawlers and
    fetchers from the
    [Googlebot documentation](https://developers.google.com/search/docs/crawling-indexing/googlebot.md.txt)
    to the
    [crawling documentation](https://developers.google.com/crawling/docs/crawlers-fetchers/overview-google-crawlers.md.txt#file-size-limits).


    **Why**: The original location of this information was not the most logical place as it
    applies to all of Google's crawlers and fetchers, and so we moved it to the crawler
    infrastructure documentation.

## January 2026

January 21
:

    ### Added Google Messages to the list of user-triggered fetchers


    **What** : Added the [Google Messages](https://developers.google.com/crawling/docs/crawlers-fetchers/google-user-triggered-fetchers.md.txt#google-messages) fetcher to the list of user-triggered fetchers.


    **Why**: To help site owners identify traffic from Google Messages when it generates link previews for URLs sent in chat messages.

## December 2025

December 18
:

    ### Migrated more documentation to the Google crawling documentation site


    **What** : Migrated the following documentation to
    [Google's crawling infrastructure site](https://developers.google.com/crawling). The functionality hasn't changed,
    only the location of the documentation and some minor wording changes to clarify that some
    guidance applies to both Google Search and other Google products.

    - [Managing crawling of faceted navigation URLs](https://developers.google.com/crawling/docs/faceted-navigation.md.txt)
    - [Optimize your crawl budget](https://developers.google.com/crawling/docs/crawl-budget.md.txt)
    - [How HTTP status codes affect Google's crawlers](https://developers.google.com/crawling/docs/troubleshooting/http-status-codes.md.txt)
    - [Debug DNS and network errors](https://developers.google.com/crawling/docs/troubleshooting/dns-network-errors.md.txt)


    **Why**: This documentation is more relevant to many Google products that use Google's crawlers,
    not just Search.

December 2
:

    ### Updated Google Read Aloud user agent page


    **What** : Updated the
    [Google Read Aloud user agent page](https://developers.google.com/crawling/docs/crawlers-fetchers/read-aloud-user-agent.md.txt)
    to provide additional details on how it functions, in particular that it uses stateless
    rendering, and that it needs to access the page to see the meta tags used on the page.


    **Why**: We received feedback through the help community that more information would be helpful.

## November 2025

November 20
:

    ### Migrated documentation to the new Google crawling documentation site


    **What** : Migrated crawling documentation from the
    [Google Search Central](https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers)
    to a new [Google crawling documentation site](https://developers.google.com/crawling). The content hasn't changed,
    only the location. Notable moves include:

    - [Overview of Google crawlers and fetchers](https://developers.google.com/crawling/docs/crawlers-fetchers/overview-google-crawlers.md.txt)
    - [Verify requests from Google crawlers and fetchers](https://developers.google.com/crawling/docs/crawlers-fetchers/verify-google-requests.md.txt)
    - [Reduce the Google crawl rate](https://developers.google.com/crawling/docs/crawlers-fetchers/reduce-crawl-rate.md.txt)
    - [Google common crawlers](https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers.md.txt)
    - [How Google interprets the robots.txt specification](https://developers.google.com/crawling/docs/robots-txt/robots-txt-spec.md.txt)


    **Why**: Google's crawling infrastructure is shared across a variety of Google products beyond Search,
    including Google Shopping, News, Gemini, AdSense, and more. The new site
    is a more logical home for this documentation and makes it easier to document new features
    and updates that are relevant to all of these products.

November 12
:

    ### Added the `Google-Pinpoint` fetcher


    **What** : We added the
    [`Google-Pinpoint`](https://developers.google.com/crawling/docs/crawlers-fetchers/google-user-triggered-fetchers.md.txt#google-pinpoint)
    fetcher to the list of user-triggered fetchers.


    **Why** : The `Google-Pinpoint` fetcher is used by the Pinpoint research tool.

November 3
:

    ### Added a new user-triggered fetcher


    **What** : Based on feedback, we added the
    [`Google-CWS`](https://developers.google.com/crawling/docs/crawlers-fetchers/google-user-triggered-fetchers.md.txt#google-cws)
    fetcher to the list of user-triggered fetchers.

## October 2025

October 15
:

    ### Updated the list of Google products that use the Read Aloud service


    **What** : Update the documentation on [Google Read Aloud](https://developers.google.com/crawling/docs/crawlers-fetchers/read-aloud-user-agent.md.txt) with an updated list of Google products that use the Read Aloud service.


    **Why**: Other Google products can now use the Google Read Aloud service.

October 9
:

    ### Added `Google-NotebookLM` to the list of user-triggered fetchers


    **What** : Based on feedback, we added
    [`Google-NotebookLM`](https://developers.google.com/crawling/docs/crawlers-fetchers/google-user-triggered-fetchers.md.txt#notebooklm)
    to the list of user-triggered fetchers.

## July 2025

July 1
:

    ### Updated the Google Read Aloud user agent


    **What** : Updated [Google Read Aloud user agent](https://developers.google.com/crawling/docs/crawlers-fetchers/google-user-triggered-fetchers.md.txt)
    in HTTP requests with newer browser versions.


    **Why**: To accommodate sites which don't support old browser versions.

## April 2025

April 25
:

    ### Updated the description of the Google-Extended product token


    **What** : Based on publisher feedback, we updated the [Google-Extended](https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers.md.txt#google-extended)
    product token description to provide additional specificity and clarity.

:

    ### Corrected the description of the crawler preferences addressed to the `Googlebot-News` user agent


    **What** : Updated the
    [`Googlebot-News`](https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers.md.txt#googlebot-news)
    user agent description.


    **Why** : The description for how crawling preferences addressed to
    `Googlebot-News` mistakenly stated that they'd affect the News tab on Google,
    which is not the case.