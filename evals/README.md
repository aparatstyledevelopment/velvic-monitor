# LLM evals

Three suites live here, all driven by Promptfoo:

- `briefing_quality/` — fixture FactPacks plus expected qualitative properties
  (citation discipline, factual fidelity, narrative coherence). Phase 1.
- `citation_discipline/` — `(question, fact_pack)` pairs; assert every numeric
  claim carries a valid `[ec_xxx]` and every `[ec_xxx]` resolves. Phase 2.
- `refusal_behavior/` — off-topic questions; assert the system refuses politely
  (no completion attempted). Phase 2.

## Discipline

1. Every bug found in production becomes a new eval fixture. Same bug never
   recurs.
2. Eval suite runs on every prompt change. Drift below threshold blocks merge.
3. Eval set grows; we never delete fixtures, only mark them as superseded.

## Running

```
make evals
```

requires API keys for the configured provider in `.env.local`.
