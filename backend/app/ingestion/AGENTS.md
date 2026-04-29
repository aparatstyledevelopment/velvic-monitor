# ingestion/AGENTS.md

Ingestion transforms read Tier-1 raw rows and write Tier-2 curated rows.

## Discipline

- No HTTP. No LLM calls. (Exception: news summarization is owned by an
  Engine tool, not an ingestion transform.)
- Idempotent on `(source, source_row_id)` upsert.
- Deterministic. Same Tier-1 input → same Tier-2 output.
- Lineage on every row: `source` + `source_row_id`.
- News deduplication by source authority (MFN > ESAP > IR RSS); record the
  others in `also_seen_in`.
