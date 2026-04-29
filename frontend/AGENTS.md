# Frontend AGENTS.md

Local rules for the React SPA. Inherits from root `AGENTS.md`.

## Stack

React 18 / TypeScript strict / Vite / Tailwind / Radix UI primitives + custom
design tokens. State: Zustand (small stores per concern). Data: TanStack Query.
Routing: React Router. Streaming: SSE via fetch + ReadableStream.

## Design system discipline

NEVER use a Tailwind utility outside our token set. Tailwind config maps utilities
to CSS variables in `src/design/tokens.css`. If you reach for a value not in the
token set, that's a bug — find or extend the token first.

NEVER reach into Radix primitives' default styles. We import unstyled from
`@radix-ui/react-*` and apply our own classes only.

Tabular numerals everywhere. The base CSS sets `font-variant-numeric: tabular-nums`
on the root.

## Component shapes

Every analytical card has the same chrome: header (title + source pill + share +
attach buttons) → body (one of the body types) → optional footer.
See `src/conversation/ResponseCard.tsx`.

Briefing card is non-interactive at the per-fact level (only collapse + the
header source button work). See design blueprint §3.1.

## Streaming

Chat completion arrives as SSE. The response card text body grows live as
`text_delta` events arrive. The typing indicator is bound to the completion
state. See `src/conversation/streaming.ts`.

## Persistence

`prefs.ts` Zustand store hydrates from localStorage in an inline `<script>` in
`index.html` BEFORE first paint, to avoid theme/size flash. Never read from
localStorage in a useEffect for prefs that affect first paint.

## Browser-back history bridge

Every modal surface (full-page screen, takeover, mobile artifact pane, dialog)
must register via `useHistoryBridge(active, onClose)`. See `src/history/bridge.ts`.

## Testing

Vitest for component unit tests. Playwright for E2E in `tests/e2e/`.
