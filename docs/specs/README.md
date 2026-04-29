# Specs

Non-trivial features start here as a markdown spec covering:

- **What it does** — one paragraph, plain language.
- **Inputs / outputs** — types, shapes, contracts.
- **Edge cases** — null, empty, oversized, type-confused, timezone, locale.
- **Test cases** — unit, property, integration, eval (where applicable).
- **Success criteria** — what "done" means.
- **Assumptions** — explicit. Anything implicit becomes a footgun later.

Specs are reviewed by humans before code generation. PRs reference the spec.
Specs live forever.

## Naming

`<area>-<feature>.md`, e.g. `engine-get_price_move.md`,
`chat-citation-parsing.md`, `frontend-history-bridge.md`.
