A valid schema ensures that the AI agent understands the structure of the data
it needs to provide.

## How the WebMCP schema validity audit fails

The audit fails if:

- A form has a `tooldescription` but is missing the `toolname` attribute.
- A form has a `toolname` but is missing the `tooldescription` attribute.
- A required form field is missing a `name` attribute.

Lighthouse also issues a warning if an optional field has a `name` but is
missing a `toolparamdescription` or an associated `<label>`.

## How to fix

1. Ensure symmetry: Always provide both a name and a description for every tool.
2. Add names to inputs: Verify that every input element within a tool form has a unique `name` attribute.
3. Provide parameter context: Add `toolparamdescription` to inputs to help the agent understand what value is expected.