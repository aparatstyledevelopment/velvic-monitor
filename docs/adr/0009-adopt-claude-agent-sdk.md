# ADR 0009 — Adopt Claude Agent SDK; deprecate multi-LLM abstraction

**Status:** Accepted, 2026-05-14. Supersedes ADR 0004.

## Context

ADR 0004 chose a hand-rolled `LLMProvider` protocol so we could swap
Anthropic / OpenAI / Google per org. Eight months in, only the Anthropic
implementation ships; the protocol is paid-for in code we maintain
(~1300 LOC of orchestrator + provider + SSE accumulator + mock) but not
in optionality realised. The chat surface keeps re-implementing what
`claude-agent-sdk` now offers natively: tool-loop control, tool-use
streaming, JSONSchema marshalling, prompt caching, retries, and an
MCP-shaped tool transport.

The Engine/Narrator contract (ADR 0003) is unchanged: every numeric claim
must still come from a deterministic engine tool result and carry an
`engine_call_id` citation. That discipline is what makes the product
trustworthy for IR teams. We need the SDK to honour it.

## Decision

Adopt `claude-agent-sdk` as the chat orchestrator's loop driver.
Engine tools are exposed through an **in-process SDK MCP server** built
fresh per turn (closures over the request's `AsyncSession`). The
**PostToolUse hook** records each tool envelope's `engine_call_id` onto
the turn state. Citation validation and the strict-prompt retry remain
in the orchestrator post-stream.

Single-shot LLM calls (topic gate, briefing narrative, news summary) do
not need the agent loop and stay on raw `httpx` via
`app/chat/anthropic_messages_client.py`.

ADR 0004 is superseded. The `LLMProvider` protocol, the
`AnthropicProvider`/`MockProvider` wrappers, and `Org.llm_provider_pref`
are removed. The product is Anthropic-only for the foreseeable future.

## Rationale

- **Maintenance burden** — we delete ~1100 LOC of provider + mock and
  inherit the SDK's tested implementations of tool-use streaming,
  message serialisation, and finish-reason mapping.
- **MCP-shaped tools** — engine tools are already pure async functions
  returning JSON envelopes. Wrapping them in `@tool` is a 25-line
  adapter; the rest of `engine/` is untouched.
- **First-class hooks** — citation discipline (capturing `engine_call_id`
  from every tool call) becomes a single PostToolUse hook instead of
  bookkeeping in the loop.
- **Future features** — sub-agents, file checkpointing, and prompt
  caching land as configuration flips, not new code.
- **Realised optionality** — multi-provider was never paid for in
  revenue; the work to ship a second provider is materially larger than
  this consolidation.

## Consequences

- **Deployment** — the SDK shells out to the Claude Code CLI. Production
  containers (DO App Platform) must include Node.js + the `claude`
  binary. Tracked separately under deployment work.
- **Auth** — the SDK uses the CLI's authentication. `ANTHROPIC_API_KEY`
  is still required for the topic gate and briefing composer (which use
  the Messages API directly).
- **Tests** — orchestrator unit tests script a `FakeSDKClient` that
  emits a deterministic message stream and invokes hooks the same way
  the production SDK would. `MockProvider` is gone.
- **Provider-agnostic chat layer** — eliminated. Any future provider
  swap is a new ADR plus a rewrite.
- **History** — multi-turn history is prepended to the SDK system prompt
  as a `<conversation_history>` block. If eval gates regress on
  cross-turn reference, move to the SDK's `session_id` resume API.
- **Cost tracking** — `ResultMessage.total_cost_usd` is the source of
  truth; the existing pricing table in `anthropic_messages_client.py`
  remains for single-shot helpers and as a fallback.

## Layout (new files)

- `backend/app/chat/sdk_mcp.py` — per-turn MCP server builder.
- `backend/app/chat/sdk_hooks.py` — `PostToolUse` hook + `TurnHookState`.
- `backend/app/chat/anthropic_messages_client.py` — single-shot helper.
- `backend/app/chat/types.py` — `ToolCall`, `ToolSpec`, `CompletionEvent`.

## Deletions

- `backend/app/chat/providers/` (entire package).
- `backend/tests/unit/test_anthropic_provider.py`.
- `Org.llm_provider_pref` is now ignored; a follow-up migration drops it.
