# chat/AGENTS.md

Conversation orchestrator. Anthropic-only (ADR 0009).

## Layout

- `orchestrator.py` — state machine for one user turn:
  load thread → persist user turn → topic gate → SDK tool loop (≤8) →
  citation parse → strict retry on uncited → persist assistant turn.
  Yields `CompletionEvent`s that the SSE helper renders to the wire.
- `sdk_mcp.py` — builds the per-turn in-process MCP server exposing
  every `@engine_tool` to the Claude Agent SDK.
- `sdk_hooks.py` — `PostToolUse` hook that captures `engine_call_id`
  from each engine tool envelope onto the turn state.
- `anthropic_messages_client.py` — single-shot Messages API helper
  used by `topic_gate.py` and `engine/drivers/briefing.py`.
- `prompts.py` — chat system prompt, strict retry, topic-gate classifier,
  refusal template. Discipline: prompt change → eval gate runs.
- `topic_gate.py` — cheap-classifier guard. Off-topic = polite refusal,
  no main-model cost.
- `tools.py` — engine registry → JSONSchema, Pydantic arg coercion,
  in-process dispatch returning the engine envelope. Used by `sdk_mcp.py`.
- `citations.py` — citation marker parsing + uncited-numeric detection.
  Shared with `engine/drivers/briefing.py`.
- `types.py` — `ToolCall`, `ToolSpec`, `CompletionEvent` data classes.
- `models.py` — `chat_thread`, `chat_turn`, `chat_engine_call`. RLS-scoped
  on `org_id` (see migration 0003).

## Discipline

- The agent loop is owned by `claude-agent-sdk`. The orchestrator drives it
  via `ClaudeSDKClient`; do not reimplement tool plumbing.
- Tool catalog comes from `engine/registry.py`. Never read curated/derived
  tables directly from `chat/`.
- Every assistant message is parsed for citation markers before persistence.
  Uncited numerics trigger a strict-prompt retry, then a UI warning.
- Topic gate (cheap-model classifier via `anthropic_messages_client`)
  runs before the expensive SDK loop. Off-topic → polite refusal.
- Tool loop bounded by `MAX_TOOL_CALLS` (8); threaded into the SDK as
  `ClaudeAgentOptions.max_turns`.

## SSE wire format

Each event is a JSON object on a single `data:` line:

- `text_delta` — `{"text": str}`
- `tool_call`  — `{"id", "name", "arguments"}` (bare engine tool name,
  the `mcp__engine__` prefix is stripped by the orchestrator)
- `tool_result` — `{"tool_call_id", "engine_call_id"}`
- `warning`    — `{"code": "uncited_numeric", "message"}`
- `done`       — `{"turn_id", "thread_id", "finish_reason",
                  "prompt_tokens", "completion_tokens", "cost_cents",
                  "model", "provider", "engine_call_ids"}`
- `error`      — `{"message"}`

## Adding tools

Register via `@engine_tool(...)` in `engine/`. The per-turn MCP server
discovers them through `engine_registry.specs_for_modules(...)`. No chat
code changes needed.
