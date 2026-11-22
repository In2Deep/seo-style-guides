---
name: google-agent
description: Check whether Google-Agent can get into a website. Google-Agent is the name Google's AI agents use when they visit a site because a person asked them to. Loads every page as Google-Agent and as the same browser without its name, and flags blocks, rate limits and challenge pages that pick on the name; lists forms and CAPTCHA widgets; notes robots.txt rules that name it; compares firewall and other blocklists with Google's current Google-Agent addresses; then walks Google's troubleshooting checks that only the site owner can answer. Use when asked whether Google's AI agent, Google-Agent or Google's user-triggered agents can reach, browse or use a site, or whether a firewall, CDN, WAF or bot rule lets it through. It reports only; changing firewall, server or site rules is a separate request.
argument-hint: <address> [blocklist file or address ...]
---

# Google-Agent check

The argument is the address of a site the user runs, for example `https://example.com` or `http://127.0.0.1:4321/`. Without one, ask which address. Any further arguments are blocklists (step 1).

The checker sends Google-Agent's name. Run it only on a site the user runs or manages; on anyone else's site it would be pretending to be Google. If that isn't clear, ask first.

This skill reports. It never submits a form. Don't change firewall, CDN, server or site settings unless the user then asks for fixes.

`read_google_doc` and `check_google_quote` come from this plugin's `google_seo_and_style_guides` server. If they are listed only as deferred tools, load them first. If they aren't available, tell the user the plugin's tool server didn't start (it needs Python 3.10 or newer, and Claude needs a restart after the plugin is installed or updated). Then use the saved pages they would have read: they are in `${CLAUDE_PLUGIN_ROOT}/guides/crawling/`. Confirm a quote with `grep -F` on a short run of its words in the saved page, since lines wrap. Don't read Google's live pages in their place.

Before step 3, read `crawlers-fetchers--allow-google-agent` with `read_google_doc`. In short: Google-Agent sends a `User-Agent` header containing `Google-Agent`, comes from the addresses in `user-triggered-agents.json`, and signs some requests with Web Bot Auth (`crawlers-fetchers--web-bot-auth`). Because a person asked for the visit, robots.txt doesn't hold it back (`crawlers-fetchers--google-user-triggered-fetchers`); only the firewall, CDN, bot service or server rules can.

## Steps

1. Unless the user gave them, ask for the site's blocklists: the lists of addresses it refuses, such as an export of the firewall's blocked set, a list of addresses a ban tool has banned, or the address of a published list the firewall loads (for example a Spamhaus DROP list). The checker reads addresses, networks and ranges in any common format. Ask for lists only, never keys or passwords. If there are none, go on without.

2. Run the checker with Python 3.10 or newer, putting the address and each blocklist in quotes:

   ```sh
   python3 -B "${CLAUDE_PLUGIN_ROOT}/agent_check.py" "https://example.com/" --blocklist "blocked.txt"
   ```

   If this skill is not running from an installed plugin, `agent_check.py` is at the root of the seo-style-guides repository. Repeat `--blocklist` for each list; `--pages N` checks more than the first 50 pages.

   It prints one PASS or FAIL line per page. FAIL means Google-Agent's name alone changed the answer: blocked, rate limited, a challenge page, or sent somewhere else. NOTICE lines name pages that turn every visitor away and in-page CAPTCHA widgets. After the pages it lists robots.txt lines that name Google-Agent, every form and where it sends, Google's address list with its date, and each blocklist entry that covers a Google-Agent address. Say how many pages it checked.

3. Ask about what the checker can't see. Its requests come from this computer, not from Google's addresses, and carry no signature. Google's troubleshooting list on the allow page has six checks; for each, ask the user or read the settings and config files they point to (CDN or firewall rules, the web server's config, rate limit and ban rules). Don't guess an answer.
   - Rule priority: does the allow rule run before broad blocks of cloud or data center networks, managed bot rules and AI agent block categories?
   - Interactive challenges: does it skip CAPTCHAs and JavaScript challenges, including the widgets from step 2?
   - In-journey actions and APIs: does it cover on-site search, filters, detail pages, cart and booking, and the requests a page's scripts make (XHR, GraphQL, `api.` addresses)? The checker sees forms in the HTML, not calls made by scripts.
   - Shared-IP rate limits: do per-address rate limits and automatic bans exempt Google-Agent's ranges? Many people's requests share one pool of addresses, so a rule that bans an address for one visitor's errors turns away everyone else using it.
   - IP range updates: how does the allow rule stay in step with `user-triggered-agents.json`? The checker prints the list's date.
   - Proxy headers: do load balancers and proxies pass on the visitor's real address, the `User-Agent` header, and the `Signature`, `Signature-Input` and `Signature-Agent` headers?

   Web Bot Auth is optional and experimental. If the site's provider supports it, verifying the signature is the stronger check, but Google doesn't sign every request, so the address and name checks are still needed.

4. Confirm every Google quote in the report with `check_google_quote`.

## Report

1. Turned away: each failed page and each blocklist entry that covers a Google-Agent address, with what Google-Agent got and the Google quote.
2. To confirm: the notices (pages that turn every visitor away, CAPTCHA widgets, forms that send to another site), then each of the six checks with the user's answer, or "not answered".
3. Not tested: requests from Google's addresses, signatures, rate limits under real load and proxy headers, except where step 3 answered them.

A robots.txt rule that names Google-Agent gets one line: it doesn't hold Google-Agent back.
