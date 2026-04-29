# Prompts

Every LLM prompt and its rationale lives here OR in a `prompts.py` near the code
that calls it. This file is the index.

## Locations

- Chat orchestrator system prompt: `backend/app/chat/prompts.py`.
- Topic classifier prompt: `backend/app/chat/prompts.py`.
- Briefing card composer prompt: `backend/app/engine/drivers/prompts.py`.
- News summary prompt: `backend/app/engine/drivers/prompts.py`.
- Output validation retry prompt: `backend/app/chat/prompts.py`.
- Smart-chip generator prompt: `backend/app/engine/drivers/prompts.py`.

Canonical text of all prompts is in the blueprint Appendix D. Code references
this file by section.

## Discipline

- Prompts are version-controlled. Every change runs the eval suite.
- A prompt change that drops eval pass-rate below threshold blocks merge.
- Bug-fix loop: production bug → fixture in `evals/` → prompt or tool fix →
  green eval → ship. Same bug never recurs.
- Prompts treat `<external_content>...</external_content>` as data, never
  as instructions.

## Provider notes

- Anthropic: prompt caching enabled on the stable system prompt + tool
  definitions block.
- OpenAI: predicted outputs where the response shape is stable.
- Google: equivalent caching via context caching API where available.

## Cost discipline

Cheap-tier model (Haiku / 4o-mini / Flash) for: classification, news summary,
smart chips, briefing narration. Expensive model for: multi-tool chat
conversations only when org's preference and budget permit.
