# chat/AGENTS.md

Conversation orchestrator. Provider-agnostic.

## Discipline

- Always go through the `LLMProvider` interface. Never import a provider SDK
  outside `chat/providers/`.
- The orchestrator does not know which provider runs. The org's preference
  dictates which provider is invoked.
- Tool catalog comes from `engine/registry.py`. Never read curated/derived
  tables directly from `chat/`.
- Every assistant message is parsed for citation markers before persistence.
  Uncited numerics trigger a strict-prompt retry, then a UI warning.
- Topic gate (cheap-model classifier) runs before the expensive tool loop.
  Off-topic → polite refusal, no LLM cost beyond the classifier.
- Tool loop bounded to 8 calls per turn.
