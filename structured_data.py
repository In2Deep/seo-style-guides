"""Check a page's JSON-LD against the required and recommended property tables in Google's saved
structured-data pages (guides/seo/appearance--structured-data--*.md) and its site names page
(`WebSite`), read at call time.

Checks only which properties are present, never their values. Fetches nothing.
"""
import json
import re
from html.parser import HTMLParser
from pathlib import Path

GUIDE_FOLDER = Path(__file__).resolve().parent / "guides" / "seo"
PAGE_PREFIX = "appearance--structured-data--"
SITE_NAME_PAGE = "appearance--site-names.md"  # where Google documents `WebSite`, outside the structured-data pages
SOURCE_PREFIX = "https://developers.google.com/search/docs/"
TYPE_DEFINITIONS_HEADING = "Structured data type definitions"
POLICY = "Policy: fill in recommended properties too, unless the site has no true value for one (never invent a value)."
NO_FEATURE = "Google documents no search feature for this type"

TABLE_HEADER = re.compile(r"^\|\s*\**(Required|Recommended) properties")
HEADING = re.compile(r"^(#+) (.*)")
CODE_NAME = re.compile(r"`([\w.@]+)`")
BARE_TYPE_HEADING = re.compile(r"([A-Z][A-Za-z]+)(?: \(.*\)| entity)?")
OPTION_ROW = re.compile(r"^\|\s*Option (\w+)\s*\|")  # "| Option A ||": required properties split into alternative sets


class JsonLdScripts(HTMLParser):
    """The text of every <script type="application/ld+json"> of an HTML page, found the way a browser finds them:
    markup inside a comment, a script of another type and anything inside <template> are left out."""

    def __init__(self, html: str):
        super().__init__(convert_charrefs=True)
        self.scripts, self.text, self.template_depth = [], None, 0
        self.feed(html)
        self.close()

    def handle_starttag(self, tag: str, attrs: list) -> None:
        script_type = next((value or "" for name, value in attrs if name == "type"), "")  # the first one counts
        if tag == "template":
            self.template_depth += 1
        elif tag == "script" and not self.template_depth and script_type.strip().lower() == "application/ld+json":
            self.text = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "template":
            self.template_depth = max(0, self.template_depth - 1)
        elif tag == "script" and self.text is not None:
            self.scripts.append("".join(self.text))
            self.text = None

    def handle_data(self, data: str) -> None:
        if self.text is not None:
            self.text.append(data)


def ld_json_scripts(html: str) -> list[str]:
    return JsonLdScripts(html).scripts


def heading_types(heading: str) -> list[str]:
    """Type names a heading documents: `Book` (`Work`) gives Book, `A` (or `B`) gives A and B."""
    outside_notes = re.sub(r"\((?!or )[^)]*(\)|$)", "", heading)
    names = CODE_NAME.findall(outside_notes)
    if not names and "`" not in heading and (bare := BARE_TYPE_HEADING.fullmatch(heading)):
        names = [bare[1]]
    return names


def read_sections() -> list[dict]:
    """Every property table section in the saved pages: page, heading, types and (kind, names) entries.

    A table belongs to the nearest heading (level 3 or deeper) that names a type; a table straight
    under "Structured data type definitions" belongs to the types in the page title. Beta pages are
    skipped. Entries with several names ("`price` or `priceSpecification.price`") mean any one will do.
    Rows after an "Option A" row belong to that option; any one complete option will do.
    """
    sections = []
    for path in sorted(GUIDE_FOLDER.glob(PAGE_PREFIX + "*.md")):
        title, stack, in_code, kind, option, page_sections = "", [], False, None, "", {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("```"):
                in_code = not in_code
            if in_code:
                continue
            if heading := HEADING.match(line):
                level, text = len(heading[1]), heading[2].strip()
                if level == 1 and "`" in text:
                    title = text
                stack = [entry for entry in stack if entry[0] < level] + [(level, text)]
                continue
            if header := TABLE_HEADER.match(line):
                kind, option = header[1].lower(), ""
                continue
            if not line.startswith("|"):
                kind = None
                continue
            if not kind or not stack or line.startswith("|---"):
                continue
            if choice := OPTION_ROW.match(line):
                option = choice[1]
                continue
            owner = None
            for level, text in reversed(stack):
                if level <= 2 or text == TYPE_DEFINITIONS_HEADING:
                    if (level, text) == stack[-1]:  # a table straight under it
                        owner = (text, CODE_NAME.findall(title))
                    break
                if names := heading_types(text):
                    owner = (text, names)
                    break
            names = tuple(CODE_NAME.findall(line.split("|")[1]))
            if owner and owner[1] and names:
                section = page_sections.setdefault(owner[0], {"heading": owner[0], "types": set(owner[1]), "entries": []})
                section["entries"].append((kind, names, option))
        if "beta" in title.lower():
            continue
        for section in page_sections.values():
            section.update(file=path.name, title=title, title_types=set(CODE_NAME.findall(title)),
                           source=SOURCE_PREFIX + path.stem.replace("--", "/"))
            sections.append(section)
    documented = set().union(*(section["types"] for section in sections))
    for file_name in {section["file"] for section in sections}:  # `Article` objects also cover NewsArticle and BlogPosting
        page_sections = [section for section in sections if section["file"] == file_name]
        if len(page_sections) == 1 and page_sections[0]["types"] <= page_sections[0]["title_types"]:
            page_sections[0]["types"] |= page_sections[0]["title_types"] - documented
    return sections + site_name_section()


def site_name_section() -> list[dict]:
    """The `WebSite` section, from the site names page. Its tables sit under headings that name no type."""
    path = GUIDE_FOLDER / SITE_NAME_PAGE
    entries, kind = [], None
    for line in path.read_text(encoding="utf-8").splitlines() if path.exists() else []:
        if header := TABLE_HEADER.match(line):
            kind = header[1].lower()
        elif not line.startswith("|"):
            kind = None
        elif kind and (names := tuple(CODE_NAME.findall(line.split("|")[1]))):
            entries.append((kind, names, ""))
    if not entries:
        return []
    return [{"heading": "Site name", "types": {"WebSite"}, "title_types": {"WebSite"}, "entries": entries,
             "file": path.name, "title": "Provide a site name to Google Search",
             "source": SOURCE_PREFIX + path.stem.replace("--", "/")}]


def item_types(item: dict) -> list[str]:
    types = item.get("@type", [])
    types = types if isinstance(types, list) else [types]
    return [str(name).rsplit("/", 1)[-1].removeprefix("schema:") for name in types]


def has_property(item: dict, path: str) -> bool | None:
    """Whether item has the (possibly dotted) property; None when the parent of a dotted one is absent or not an object."""
    head, _, rest = path.partition(".")
    value = item.get(head)
    if not rest:
        return value not in (None, "", [], {})
    children = [child for child in (value if isinstance(value, list) else [value]) if isinstance(child, dict)]
    if not children:
        return None
    return all(has_property(child, rest) for child in children)


def missing(item: dict, entries: list[tuple[str, tuple[str, ...], str]], kind: str, optional: tuple[str, ...] = ()) -> list[str]:
    absent, options = [], {}
    for entry_kind, names, option in entries:
        if entry_kind != kind or names[0] in optional:
            continue
        found = [has_property(item, name) for name in names]
        gap = not any(found) and not (len(names) == 1 and found[0] is None)
        label = names[0] if len(names) == 1 else "one of " + " or ".join(names)
        if option:
            options.setdefault(option, []).extend([label] if gap else [])
        elif gap and label not in absent:
            absent.append(label)
    if options and all(options.values()):  # no option is complete
        absent.append("one option of " + " or ".join(f"{key} ({', '.join(labels)})" for key, labels in options.items()))
    return absent


def check_against(item: dict, section: dict, sections: list[dict], indent: str, optional: tuple[str, ...] = ()) -> list[str]:
    lines = []
    for kind in ("required", "recommended"):
        names = missing(item, section["entries"], kind, optional)
        lines.append(f"{indent}{kind}, missing: {', '.join(names) if names else 'none'}")
    for name, value in item.items():
        children = value if isinstance(value, list) else [value]
        for child in children:
            if not isinstance(child, dict) or "@type" not in child:
                continue
            for child_type in item_types(child):
                for child_section in sections:
                    if child_section["file"] == section["file"] and child_type in child_section["types"]:
                        lines.append(f"{indent}nested {child_type} in {name} ({child_section['heading']}):")
                        last_crumb = child is children[-1] and child_type == "ListItem" and section["file"].endswith("--breadcrumb.md")
                        # Google: the last item in the breadcrumb trail may omit `item`
                        lines.extend(check_against(child, child_section, sections, indent + "  ", ("item",) if last_crumb else ()))
    return lines


def json_ld_items(markup: str) -> list[dict]:
    """The top-level items with an @type in JSON-LD text or in every ld+json script of an HTML page."""
    is_html = markup.lstrip().startswith("<")
    blocks = ld_json_scripts(markup) if is_html else [markup]
    items = []
    for number, block in enumerate(blocks, 1):
        try:
            data = json.loads(block)
        except json.JSONDecodeError as error:
            where = f"JSON-LD script block {number}" if is_html else "The markup"
            raise ValueError(f"{where} is not valid JSON: {error}") from None
        for entry in data if isinstance(data, list) else [data]:
            if isinstance(entry, dict):
                graph = entry.get("@graph")
                items.extend(graph if isinstance(graph, list) else [entry])
    return [item for item in items if isinstance(item, dict) and "@type" in item]


def check_structured_data(markup: str) -> str:
    if markup.lstrip().startswith("<") and not ld_json_scripts(markup):
        return 'No <script type="application/ld+json"> block found in the HTML.'
    items = json_ld_items(markup)
    if not items:
        return "No JSON-LD item with an @type found."
    sections = read_sections()
    report = [POLICY]
    for number, item in enumerate(items, 1):
        types = item_types(item)
        report.append(f"\nItem {number}: {', '.join(types)}")
        matched = [s for s in sections if s["types"] & s["title_types"] & set(types)]
        if not matched:
            report.append(f"  {NO_FEATURE} (matched by exact type name; subtypes such as a LocalBusiness subtype are not mapped).")
        for section in matched:
            report.append(f"  page: guides/seo/{section['file']}: {section['title']} [{section['heading']}]")
            report.append(f"  source: {section['source']}")
            report.extend(check_against(item, section, sections, "  "))
    return "\n".join(report)
