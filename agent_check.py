#!/usr/bin/env python3
"""Checks whether Google-Agent can get into a website, each check tied to Google's own words.

Google-Agent is the name Google's AI agents use when they visit a site because a person asked them to.
For each page found under the address (the sitemap first, then links, up to --pages), this loads the page
twice: once with Google-Agent's published User-Agent string, and once with the same browser string without
Google-Agent in it. Any difference in the answer is a rule that turns the agent away by name. It also lists
the site's forms and in-page CAPTCHA widgets, reads robots.txt, and, given --blocklist files or addresses,
compares their addresses with Google's current list of Google-Agent addresses (user-triggered-agents.json).

What it can't see: the requests come from this computer, not from Google's addresses, and carry no Web Bot
Auth signature, so rules that trust Google's addresses or signatures are not tested here (--blocklist
compares address rules on paper). It sends Google-Agent's name, so run it on sites you run. It never submits
a form. Every quote is word for word from a saved page in guides/crawling (a test confirms each one).
Needs Python 3.10 or newer.

Run: python3 agent_check.py https://site/ [--blocklist FILE_OR_URL ...] [--pages N]   (exit status 1 if any check fails)
"""
import argparse
import ipaddress
import json
import re
import sys
from html.parser import HTMLParser
from http.client import HTTPException, IncompleteRead
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

import page_check

FETCHERS = "https://developers.google.com/crawling/docs/crawlers-fetchers/"
ALLOW_PAGE = FETCHERS + "allow-google-agent"
USER_TRIGGERED_PAGE = FETCHERS + "google-user-triggered-fetchers"
AGENT_RANGES_URL = "https://developers.google.com/static/crawling/ipranges/user-triggered-agents.json"
USER_TRIGGERED_FILE = Path(__file__).resolve().parent / "guides" / "crawling" / "crawlers-fetchers--google-user-triggered-fetchers.md"
CHROME_VERSION = "148.0.0.0"  # stands in for Google's W.X.Y.Z; both requests send the same one
MAX_PAGES = 50
FETCH_TIMEOUT = 20
MAX_BODY_BYTES = 2_000_000
TURNED_AWAY = {401, 403, 406, 407, 409, 418, 429, 451, 503}  # answers that refuse the visitor

# A page that stands in for the real one while a service decides whether the visitor is a person.
CHALLENGE_HEADERS = (("cf-mitigated", "challenge", "Cloudflare"), ("x-amzn-waf-action", "", "AWS WAF"),
                     ("x-vercel-mitigated", "challenge", "Vercel"), ("x-datadome", "", "DataDome"))
CHALLENGE_MARKERS = (("/cdn-cgi/challenge-platform/", "Cloudflare"), ("cf-chl-", "Cloudflare"),
                     ("captcha-delivery.com", "DataDome"), ("px-captcha", "HUMAN (PerimeterX)"),
                     ("/_sec/cp_challenge/", "Akamai"), ("_incapsula_resource", "Imperva"),
                     ("incapsula incident id", "Imperva"), ("sucuri website firewall", "Sucuri"),
                     ("awswaf.com", "AWS WAF"), ("vercel security checkpoint", "Vercel"))
UNNAMED_CHALLENGE = "unnamed"  # a challenge page known only by its title and a refusing status
CHALLENGE_TITLES = re.compile(r"<title>[^<]*(just a moment|attention required|access denied|are you a robot|"
                              r"verify you are human|security check|captcha|checking your browser)", re.I)
# In-page CAPTCHA widgets: a script address, or a class on the element the widget fills.
WIDGET_SCRIPTS = (("google.com/recaptcha/", "reCAPTCHA"), ("recaptcha.net/recaptcha/", "reCAPTCHA"),
                  ("hcaptcha.com/1/api.js", "hCaptcha"), ("challenges.cloudflare.com/turnstile", "Cloudflare Turnstile"),
                  ("friendlycaptcha", "Friendly Captcha"), ("captcha.awswaf.com", "AWS WAF CAPTCHA"))
WIDGET_CLASSES = {"g-recaptcha": "reCAPTCHA", "h-captcha": "hCaptcha", "cf-turnstile": "Cloudflare Turnstile",
                  "frc-captcha": "Friendly Captcha"}
SEARCH_FIELD_NAMES = {"q", "s", "query", "search", "keyword", "keywords"}

CHECKS = [
    {"name": "gets in by name", "source": ALLOW_PAGE,
     "quote": "Explicitly allowing `Google-Agent` traffic in your content delivery network (CDN), web application firewall (WAF), or bot-detection service helps prevent legitimate requests from being blocked while preserving your existing security controls."},
    {"name": "rate limits", "source": ALLOW_PAGE,
     "quote": "Confirm that per-IP rate-limiting rules account for or exempt verified `Google-Agent` IP ranges, as concurrent requests from multiple users share the same egress pool."},
    {"name": "challenges", "source": ALLOW_PAGE,
     "quote": "Confirm that your rule skips interactive CAPTCHAs and JavaScript challenges in addition to HTTP blocks, including standalone in-page CAPTCHA widgets triggered on search or form submission."},
    {"name": "forms and APIs", "source": ALLOW_PAGE,
     "quote": "Confirm that allowing these requests covers actions beyond initial homepage loads, including on-site search, filtering, clicking into detail pages, add-to-cart, booking, and underlying XHR, GraphQL, or `api.*` endpoints."},
    {"name": "robots.txt", "source": USER_TRIGGERED_PAGE,
     "quote": "Because the fetch was requested by a user, these fetchers generally ignore robots.txt rules."},
    {"name": "blocklists", "source": ALLOW_PAGE,
     "quote": "Confirm that your allow rule has higher priority than (and evaluates before) broad cloud or data center ASN blocks, managed bot rules, or category-level AI agent block policies that could override a verified bot setting."},
]
CHECK = {check["name"]: check for check in CHECKS}


def agent_user_agent() -> tuple[str, str]:
    """Google-Agent's mobile User-Agent string from the saved page, and the same string without Google-Agent."""
    section = USER_TRIGGERED_FILE.read_text(encoding="utf-8").partition("## Google-Agent")[2].partition("\n## ")[0]
    strings = [line.strip() for line in section.splitlines() if line.strip().startswith("Mozilla/") and "Google-Agent;" in line]
    mobile = next((string for string in strings if " Mobile " in string), None)
    if mobile is None:
        sys.exit(f"Found no Google-Agent mobile User-Agent string in {USER_TRIGGERED_FILE}; Google may have changed the page.")
    agent = mobile.replace("W.X.Y.Z", CHROME_VERSION)
    browser = re.sub(r" \(compatible; Google-Agent; \+[^)]*\)|; compatible; Google-Agent; \+[^)]*", "", agent)
    return agent, browser


def load(url: str, user_agent: str) -> dict:
    """One GET request. An error status still counts as an answer; a refused or dropped connection has status None."""
    request = Request(url, headers={"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                                    "Accept-Language": "en"})
    try:
        response = urlopen(request, timeout=FETCH_TIMEOUT)
    except HTTPError as error:
        response = error
    except (OSError, ValueError) as error:  # refused, dropped (RemoteDisconnected is an OSError) or timed out
        return {"status": None, "error": str(getattr(error, "reason", error)), "url": url, "headers": {}, "text": ""}
    except HTTPException as error:  # the answer wasn't HTTP at all
        return {"status": None, "error": f"a garbled answer ({type(error).__name__})", "url": url, "headers": {}, "text": ""}
    try:
        with response:
            body = response.read(MAX_BODY_BYTES)
    except IncompleteRead as error:  # the answer was cut short: keep what came
        body = error.partial
    except (OSError, ValueError, AttributeError, HTTPException):  # an error answer with no body, or a dropped connection
        body = b""
    headers = {name.lower(): value for name, value in response.headers.items()}
    text = body.decode(response.headers.get_content_charset() or "utf-8", errors="replace")
    return {"status": response.status, "error": "", "url": response.geturl(), "headers": headers, "text": text}


def challenge(answer: dict) -> str:
    """The service whose challenge page this answer is, UNNAMED_CHALLENGE, or "".

    A marker or a title alone is not enough on a page that was served normally: Cloudflare adds its challenge
    script to ordinary pages, and an ordinary page can be about CAPTCHAs."""
    for header, value, service in CHALLENGE_HEADERS:
        if header in answer["headers"] and value in answer["headers"][header].lower():
            return service
    text = answer["text"][:200_000].lower()
    refused = answer["status"] in TURNED_AWAY
    titled = bool(CHALLENGE_TITLES.search(answer["text"][:20_000]))
    for marker, service in CHALLENGE_MARKERS:
        if (refused or titled) and marker in text:
            return service
    return UNNAMED_CHALLENGE if refused and titled else ""


def outcome(answer: dict) -> str:
    """What the visitor got, in a few words, or "" when it got the page."""
    if answer["status"] is None:
        return f"no answer ({answer['error']})"
    service = challenge(answer)
    if service:
        return f"HTTP {answer['status']}, " + ("a challenge page" if service == UNNAMED_CHALLENGE else f"{service} challenge page")
    if answer["status"] in TURNED_AWAY or answer["status"] >= 400:
        return f"HTTP {answer['status']}"
    return ""


class FormParser(HTMLParser):
    """Each <form>: where it sends, how, whether it is a search, and the CAPTCHA widgets inside it."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.forms: list[dict] = []
        self.widgets: set[str] = set()  # widget elements anywhere on the page
        self._form: dict | None = None

    def handle_starttag(self, tag, attrs):
        attributes = {name: value or "" for name, value in attrs}
        if tag == "form":
            self._form = {"action": attributes.get("action", "").strip(), "method": (attributes.get("method") or "get").lower(),
                          "search": attributes.get("role", "").lower() == "search", "widgets": set()}
            self.forms.append(self._form)
            return
        for name in attributes.get("class", "").split():
            if name in WIDGET_CLASSES:
                self.widgets.add(WIDGET_CLASSES[name])
                if self._form is not None:
                    self._form["widgets"].add(WIDGET_CLASSES[name])
        if self._form is not None and tag == "input" and (
                attributes.get("type", "").lower() == "search" or attributes.get("name", "").lower() in SEARCH_FIELD_NAMES):
            self._form["search"] = True

    def handle_endtag(self, tag):
        if tag == "form":
            self._form = None


def page_widgets(html: str, parser: FormParser) -> set[str]:
    lowered = html.lower()
    return parser.widgets | {name for marker, name in WIDGET_SCRIPTS if marker in lowered}


def read_networks(text: str) -> list:
    """Every IP address, network or range written in a blocklist, in any common format (plain lists, nftables sets,
    iptables rules, fail2ban lists, Spamhaus DROP). Anything that isn't a valid address is skipped."""
    networks = []
    for start, end in re.findall(r"(?<![\w.])((?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?)(?:\s*-\s*((?:\d{1,3}\.){3}\d{1,3}))?(?![\w.])", text):
        try:
            if end:
                networks += ipaddress.summarize_address_range(ipaddress.ip_address(start), ipaddress.ip_address(end))
            else:
                networks.append(ipaddress.ip_network(start, strict=False))
        except ValueError:
            continue
    for candidate in re.findall(r"(?<![\w:.])([0-9a-fA-F]{0,4}(?::[0-9a-fA-F]{0,4}){2,7}(?:/\d{1,3})?)(?![\w:])", text):
        try:
            networks.append(ipaddress.ip_network(candidate, strict=False))
        except ValueError:
            continue
    return networks


def read_blocklist(name: str) -> str:
    if name.startswith(("http://", "https://")):
        answer = load(name, page_check.USER_AGENT)
        if answer["status"] != 200:
            raise OSError(outcome(answer) or f"HTTP {answer['status']}")
        return answer["text"]
    return Path(name).expanduser().read_text(encoding="utf-8", errors="replace")


def agent_networks() -> tuple[list, str]:
    """Google's current Google-Agent address ranges and the date of the list."""
    answer = load(AGENT_RANGES_URL, page_check.USER_AGENT)
    if answer["status"] != 200:
        raise OSError(outcome(answer) or f"HTTP {answer['status']}")
    ranges = json.loads(answer["text"])
    networks = [ipaddress.ip_network(prefix.get("ipv4Prefix") or prefix["ipv6Prefix"], strict=False) for prefix in ranges["prefixes"]]
    return networks, ranges.get("creationTime", "")[:10]


def overlaps(blocked: list, google: list) -> list[tuple]:
    return [(entry, network) for entry in blocked for network in google
            if entry.version == network.version and entry.overlaps(network)]


def robots_agent_lines(origin: str, browser: str) -> list[str]:
    """The robots.txt lines that name Google-Agent."""
    answer = load(origin + "/robots.txt", browser)
    if answer["status"] != 200:
        return []
    return [line.strip() for line in answer["text"].splitlines()
            if re.match(r"\s*user-agent\s*:.*google-agent", line, re.I)]


def cite(check: dict, indent: str = "    ") -> None:
    print(f'{indent}Google: "{check["quote"]}"', f"{indent}source: {check['source']}", sep="\n")


def say(level: str, check: dict | None, found: str, indent: str = "  ") -> None:
    """One finding; with a check, followed by the Google quote it rests on."""
    print(f"{indent}{level} {check['name'] + ': ' if check else ''}{found}")
    if check:
        cite(check, indent + "  ")


def refused(answer: dict) -> bool:
    """True when the answer turns the visitor away, not just a missing page or a server error."""
    return answer["status"] is None or answer["status"] in TURNED_AWAY or bool(challenge(answer))


def check_pages(start: str, agent: str, browser: str, limit: int, forms: dict) -> tuple[int, int, int]:
    """Loads each page as the browser and as Google-Agent and prints what differs. Returns pages, passed, failed."""
    passed = failed = 0
    for count, (url, _, page) in enumerate(page_check.site_pages(start, browser), 1):
        if count > limit:
            print(f"Stopped after {limit} pages; use --pages for more.\n")
            break
        if isinstance(page, str):  # the crawler's own browser request failed: load it again to see the answer
            as_browser = load(url, browser)
        else:
            as_browser = {"status": 200, "error": "", "url": page[0], "headers": {}, "text": page[2]}
        as_agent = load(url, agent)
        browser_got, agent_got = outcome(as_browser), outcome(as_agent)
        problems, notices = [], []
        if as_agent["status"] is None and as_browser["status"] is None:
            problems.append((None, f"could not reach the page: neither request got an answer ({as_agent['error']}). "
                                   "If this computer's address is banned there, this check can't tell anything"))
        elif agent_got and not browser_got:
            problems.append((CHECK["challenges" if "challenge" in agent_got else "rate limits" if as_agent["status"] == 429
                                   else "gets in by name"], f"Google-Agent got {agent_got}; the same browser without its name got the page"))
        elif agent_got and browser_got and refused(as_agent):
            notices.append((CHECK["challenges" if "challenge" in agent_got else "gets in by name"],
                            f"every visitor is turned away here: Google-Agent got {agent_got}, the browser got {browser_got}. "
                            "Google-Agent from Google's addresses gets in only if your allow rule runs before this"))
        elif agent_got and browser_got:
            notices.append((None, f"both got {agent_got}" if agent_got == browser_got
                            else f"Google-Agent got {agent_got}, the browser got {browser_got}"))
        elif not agent_got and urlsplit(as_agent["url"])[1:3] != urlsplit(as_browser["url"])[1:3]:
            problems.append((CHECK["gets in by name"], f"Google-Agent was sent to {as_agent['url']}; the browser went to {as_browser['url']}"))
        elif browser_got:
            notices.append((None, f"the browser got {browser_got}, but Google-Agent got the page"))
        html = as_agent["text"] if not agent_got else as_browser["text"] if not browser_got else ""
        if html:
            parser = FormParser()
            parser.feed(html)
            final = as_agent["url"] if not agent_got else as_browser["url"]
            for form in parser.forms:
                key = (form["method"].upper(), urljoin(final, form["action"]) if form["action"] else final.split("?")[0])
                entry = forms.setdefault(key, {"pages": set(), "search": False, "widgets": set()})
                entry["pages"].add(url)
                entry["search"] |= form["search"]
                entry["widgets"] |= form["widgets"]
            loose = page_widgets(html, parser) - {name for form in parser.forms for name in form["widgets"]}
            if loose:
                notices.append((CHECK["challenges"], f"in-page CAPTCHA widget ({', '.join(sorted(loose))}); "
                                                     "make sure verified Google-Agent requests skip it"))
        failed, passed = failed + bool(problems), passed + (not problems)
        print(f"FAIL {url} ({len(problems)} failed)" if problems else f"PASS {url}")
        for check, found in problems:
            say("FAIL", check, found)
        for check, found in notices:
            say("NOTICE", check, found)
        if problems or notices:
            print()
    return passed + failed, passed, failed


def print_forms(forms: dict) -> None:
    if not forms:
        print("Forms: none found.\n")
        return
    print(f"Forms ({len(forms)}): Google-Agent may need each one. This check never submits a form.")
    for (method, action), entry in sorted(forms.items(), key=lambda item: -len(item[1]["pages"])):
        details = ["search"] if entry["search"] else []
        if entry["widgets"]:
            details.append(f"CAPTCHA: {', '.join(sorted(entry['widgets']))}")
        print(f"  {method} {action} (on {len(entry['pages'])} page{'s' * (len(entry['pages']) != 1)}"
              f"{'; ' + '; '.join(details) if details else ''})")
    if any(entry["widgets"] for entry in forms.values()):
        say("NOTICE", CHECK["challenges"], "a form above has a CAPTCHA widget; make sure verified Google-Agent requests skip it")
    cite(CHECK["forms and APIs"], "  ")
    print()


def plural(count: int, word: str) -> str:
    return f"{count} {word}{'s' * (count != 1)}"


def check_blocklists(names: list[str]) -> tuple[bool, list[str]]:
    """Compares each blocklist with Google's Google-Agent ranges. Returns whether any covers them, and what couldn't be read."""
    try:
        google, dated = agent_networks()
    except (OSError, ValueError, KeyError, HTTPException) as error:
        print(f"FAIL blocklists: could not read Google's address list ({error}): {AGENT_RANGES_URL}\n")
        return False, ["Google's address list"]
    versions = [sum(network.version == version for network in google) for version in (4, 6)]
    print(f"Google-Agent's addresses: {len(google)} ranges ({versions[0]} IPv4, {versions[1]} IPv6), Google's list dated {dated}.")
    if not names:
        print("  No --blocklist given, so no address rules were compared.\n")
        return False, []
    any_blocked, unread = False, []
    for name in names:
        try:
            blocked = read_networks(read_blocklist(name))
        except (OSError, ValueError, HTTPException) as error:
            print(f"FAIL {name}: could not read it ({error})")
            unread.append(name)
            continue
        hits = overlaps(blocked, google)
        if not blocked:
            print(f"NOTICE {name}: no IP addresses found in it")
        elif hits:
            any_blocked = True
            print(f"FAIL {name}: {len(blocked)} entries, {len(hits)} cover{'s' * (len(hits) == 1)} Google-Agent's addresses")
            for entry, network in hits[:20]:
                print(f"  {entry} covers Google-Agent's {network}")
            if len(hits) > 20:
                print(f"  and {len(hits) - 20} more")
            print("  An allow rule for Google-Agent has to run before these.")
            cite(CHECK["blocklists"], "  ")
        else:
            print(f"PASS {name}: {len(blocked)} entries, none cover Google-Agent's addresses")
    print()
    return any_blocked, unread


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("address", help="the site to check, such as https://example.com/")
    parser.add_argument("--blocklist", action="append", default=[], metavar="FILE_OR_URL",
                        help="a list of blocked addresses to compare with Google-Agent's (repeat for more)")
    parser.add_argument("--pages", type=int, default=MAX_PAGES, help=f"how many pages to check (default {MAX_PAGES})")
    args = parser.parse_args()
    if not args.address.startswith(("http://", "https://")):
        parser.error("give a web address that starts with http:// or https://")
    if args.pages < 1:
        parser.error("--pages must be 1 or more")
    agent, browser = agent_user_agent()
    start = args.address
    parts = urlsplit(start)
    print(f"Google-Agent: {agent}\nBrowser:      {browser}\n")
    forms: dict = {}
    pages, passed, failed = check_pages(start, agent, browser, args.pages, forms)
    print()
    robots = robots_agent_lines(f"{parts.scheme}://{parts.netloc}", browser)
    if robots:
        say("NOTICE", CHECK["robots.txt"], f"robots.txt names Google-Agent ({'; '.join(robots)}), but those rules don't hold it back", "")
        print()
    print_forms(forms)
    blocked, unread = check_blocklists(args.blocklist)
    print(f"{start}: {plural(pages, 'page')} checked, {passed} passed, {failed} failed"
          f"{'; a blocklist covers Google-Agent' if blocked else ''}"
          f"{'; could not read ' + ', '.join(unread) if unread else ''}.")
    print("Not tested from here: requests from Google's addresses, Web Bot Auth signatures, rate limits under load, "
          "and whether proxies keep the headers.")
    return 1 if failed or blocked or unread else 0


if __name__ == "__main__":
    sys.exit(main())
