# chat/AGENTS.md

Conversation orchestrator. Provider-agnostic.

## Layout

- `providers/` — `LLMProvider` protocol + Anthropic / mock implementations.
- `prompts.py` — chat system prompt, strict retry, topic-gate classifier,
  refusal template. Discipline: prompt change → eval gate runs.
- `topic_gate.py` — cheap-classifier guard. Off-topic = polite refusal,
  no main-model cost.
- `tools.py` — bridges provider `ToolCall`s to the engine registry. Builds
  JSON-Schema input specs; coerces dict args via Pydantic; returns the
  engine_call_id + serialized envelope to feed back as a tool message.
- `orchestrator.py` — state machine for one user turn:
  load thread → persist user turn → topic gate → tool loop (≤8) →
  citation parse → strict retry on uncited → persist assistant turn.
  Yields `CompletionEvent`s that the SSE helper renders to the wire.
- `models.py` — `chat_thread`, `chat_turn`, `chat_engine_call`. RLS-scoped
  on `org_id` (see migration 0003).
- `citations.py` — citation marker parsing + uncited-numeric detection.
  Shared with `engine/drivers/briefing.py`.

## Discipline

- Always go through the `LLMProvider` interface. Never import a provider SDK
  outside `chat/providers/`.
- The orchestrator does not know which provider runs. The org's preference
  dictates which provider is invoked (`org.llm_provider_pref`).
- Tool catalog comes from `engine/registry.py`. Never read curated/derived
  tables directly from `chat/`.
- Every assistant message is parsed for citation markers before persistence.
  Uncited numerics trigger a strict-prompt retry, then a UI warning.
- Topic gate (cheap-model classifier) runs before the expensive tool loop.
  Off-topic → polite refusal, no LLM cost beyond the classifier.
- Tool loop bounded to 8 calls per turn. Cap-hit re-invokes the model with
  `tools=None` to force a final answer.

## SSE wire format

Each event is a JSON object on a single `data:` line:

- `text_delta` — `{"text": str}`
- `tool_call`  — `{"id", "name", "arguments"}`
- `tool_result` — `{"tool_call_id", "engine_call_id"}` (or `error`)
- `warning`    — `{"code": "uncited_numeric", "message"}`
- `done`       — `{"turn_id", "thread_id", "finish_reason",
                  "prompt_tokens", "completion_tokens", "cost_cents",
                  "model", "provider", "engine_call_ids"}`
- `error`      — `{"message"}`

## Adding tools

Register via `@engine_tool(...)` in `engine/`. The chat orchestrator picks
them up automatically through `tool_specs_for_chat(modules=...)`. No chat
code changes needed.
