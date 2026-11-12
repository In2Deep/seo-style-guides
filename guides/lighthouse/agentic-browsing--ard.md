Agentic Resource Discovery (ARD) is a specification for cataloging agentic
resources. The `ard.json` manifest describes agentic resources on a domain, such
as MCP servers, A2A agents, and agent skills, so that AI agents and registries
can find them.

## How the Lighthouse audit works

**Discovery process:** The audit looks for the manifest based on the discovery
mechanisms in the ARD specification (§5.1):

- Checking for an `Agentmap:` directive inside `robots.txt`.
- Scanning HTML for `<link rel="ard" href="...">` tags.
- Inspecting for an HTTP `Link: <...>; rel="ard"` header response.
- Fetching from the well-known endpoint `/.well-known/ard.json`.

If primary discovery fails, Lighthouse checks legacy pathways (such as
`rel="ai-catalog"` or `/.well-known/ai-catalog.json`). While content found here
is still validated, a warning is raised because standard ARD clients are not
obligated to support deprecated routes.

**Validation rules:** Verification is performed using a JavaScript port of the
ARD v0.91
[conformance suite](https://github.com/ards-project/ard-spec/blob/main/conformance/bin/conformance-test),
testing for the following criteria:

**Conformance and validation errors:**

- **Syntax and schema:** The manifest is valid JSON and matches the ARD manifest schema, and each entry matches the ARD entry schema. Lighthouse doesn't fetch or validate the artifact an entry points to (for example, the MCP server card at `url`).
- **Required fields:** The manifest contains an `entries` array, and every entry contains an `identifier`, `displayName`, and `type`.
- **Domain-anchored URNs:** Each `identifier` follows the `urn:air:<publisher>:<namespace>:<name>` format.
- **Location definition:** Each entry defines exactly one of `url` or inline `data`, never both or neither.
- **Trust manifest structure:** When a `trustManifest` is included, it is an object with an `identity` property.

**Best practice warnings:**

- **Representative queries:** Each entry has a `representativeQueries` array with 2--5 sample queries. Registries build their search index from these, so an entry without them won't appear in search results. (If present, it must be an array of strings; anything else is an error.)
- **Media type:** `type` must be a well-formed media type. Lighthouse warns about deprecated types (for example, `application/mcp-server+json` to `application/mcp-server-card+json`), standard types with missing or extra parameters, and unrecognized types outside `application/*`. Custom `application/*` types are allowed.
- **Collections:** Flags a top-level `collections` field. It's no longer part of ARD and is ignored; model hierarchies inside `entries` instead.
- **Legacy endpoints:** Flags manifests that are only found through the legacy `ai-catalog` locations.
- **Broken advertised locations:** Flags any advertised location (`Agentmap:`, `rel="ard"` or `rel="ai-catalog"` link, or `Link` header) that couldn't be loaded when the manifest was found somewhere else.

**Not required:**

- `specVersion` and other extra top-level fields don't affect the score.
- `capabilities` are optional and not scored. If your resource exposes named tools or skills, consider listing them (for example, `["WeatherTool", "ForecastTool"]`) so registries can filter on them without fetching the full artifact. If included, it must be an array of strings.

## Reading the results table

The Element column shows `Root` for problems with the manifest as a whole. For
problems with an entry, it shows the entry's `displayName`, falling back to its
`identifier`, or `Entry #n` if neither is available. A single schema problem may
appear twice, once under `Root` and once under the entry, matching the output of
the official conformance test.

## Understand your score

The audit results are reflected in the following ways:

- **Pass (1):** The manifest was found and has no errors or warnings.
- **Partial credit (0.9):** The manifest is valid but has at least one best-practice warning.
- **Fail (0):** Any conformance error, such as malformed JSON, a schema violation, an invalid URN, or both or neither of `url/data`. The audit also fails if a manifest was advertised (through `robots.txt`, a `rel="ard"` or `rel="ai-catalog"` link, or a `Link` header) but couldn't be loaded.
- **Not applicable:** No manifest was found by any method. This doesn't affect your Lighthouse score.

## How to fix

To pass the audit, follow these actionable steps:

1. Serve your manifest at `/.well-known/ard.json`, or link to it with `rel=ard`. If you use `ai-catalog.json` or `rel=ai-catalog`, move to the new names.
2. Fix any errors listed in the audit table so the manifest matches the ARD [schema](https://agenticresourcediscovery.org/spec/).
3. Give every entry a `urn:air:...` identifier and exactly one of `url` or `data`.
4. Use a standard ARD media type in `type` where one applies.
5. Add 2 to 5 `representativeQueries` to each entry to get a perfect score.