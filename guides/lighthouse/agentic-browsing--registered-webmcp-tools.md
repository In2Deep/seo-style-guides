Registered tools are the specific capabilities (like "Book a Table" or "Add to
Cart") that your website exposes to AI agents.

## How the Registered WebMCP tools audit works

This audit is informational. Lighthouse lists all WebMCP tools registered on the
page using the Declarative or Imperative APIs. If no tools are registered, the
result list will be empty.

Lighthouse issues a warning when more than 40 tools are registered.
By including a high excess of tools, you are likely to consume model
context tokens, add latency, and increase the risk of confusion for
agents as to what tool to use.

## How to fix

You can register tools using either the Declarative API or the Imperative API:

- Declarative API: Add `toolname` and `tooldescription` attributes directly to your `<form>` elements.
- Imperative API: Use JavaScript to register tools using `document.modelContext.registerTool`.

## Best practices

- Use clear, action-oriented names (for example, `toolname="book_appointment"`).
- Provide detailed descriptions that explain what the tool does and when an agent should use it.
- Avoid registering more than 40 tools at once. Register tools only when they're useful for the current page state, and unregister them when they're no longer needed.
- If you want to learn more, read the [WebMCP documentation](https://developer.chrome.com/docs/ai/webmcp.md.txt).