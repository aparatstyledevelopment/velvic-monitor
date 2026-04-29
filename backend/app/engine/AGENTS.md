# engine/AGENTS.md

The deterministic computation layer. Engine tools are exposed to the LLM.

## HARD RULES

- Engine tools NEVER call HTTP. NEVER call the LLM. (Exception: the briefing
  composer in `engine/drivers/briefing.py` calls the Narrator AFTER assembling
  a deterministic FactPack — the LLM call is wrapped, not embedded in tool
  logic.)
- Read only Tier-2 curated and Tier-3 derived. Never Tier-1 raw.
- Every tool returns `EngineResult[T]` with `engine_call_id`, `data`, `sources`.
- Idempotent + deterministic: same params at same `as_of_date` → same result.
- Content-addressed cache reuse via `id = hash(tool_name + canonical_params + as_of)`.

## Adding a tool

See `docs/playbooks/add-new-engine-tool.md`.
