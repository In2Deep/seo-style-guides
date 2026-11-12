While agents can often infer how a form works, providing declarative WebMCP
metadata makes interaction more reliable.

## How the Forms missing declarative WebMCP audit works

Lighthouse identifies `<form>` elements that don't have both a `toolname` and a
`tooldescription`. For now, this audit is informational and does not result in
any warnings.

## How to fix

Update your HTML forms to include the necessary WebMCP attributes:

```html
<form toolname="newsletter_signup" tooldescription="Subscribes the user to the weekly newsletter">
  <input name="email" type="email" toolparamdescription="The user's email address">
  <button type="submit">Sign Up</button>
</form>
```