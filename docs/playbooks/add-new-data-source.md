# Add a new data source

## Steps

1. **Spec.** `docs/specs/source-<name>.md` covering: endpoint, auth, cadence,
   rate limits, response schema, ToS posture, known issues.
2. **ToS check.** Confirm we may ingest and redistribute. If unclear, escalate
   before writing code.
3. **Schema.** Alembic migration adding a new Tier-1 raw table mirroring the
   upstream payload + `raw_payload jsonb` + standard lineage columns.
4. **Crawler.** `backend/app/crawlers/<name>.py` subclassing `BaseCrawler`.
   - `fetch_batches(window)` — HTTP + polite intervals.
   - `parse(batch)` — validate + extract typed columns.
   - `upsert_raw(rows)` — idempotent on natural primary key.
   - One `crawl_run` row per invocation.
5. **Schedule.** Add to `pipeline/schedules.py` Celery beat schedule.
6. **Ingestion.** Either:
   - Extend an existing transform in `ingestion/` if the source feeds an
     existing curated topic (e.g., another news source).
   - Or add a new transform if it's a new topic.
7. **Update `docs/DATA_SOURCES.md`** with the per-source row.
8. **Tests.** Crawler unit tests with fixture payloads; integration test
   crawl→ingest→engine read.

## Discipline

- Preserve `raw_payload` verbatim.
- Honor `If-Modified-Since` / ETag where supported.
- Backoff exponentially on 429/503.
- Never blend sources in Tier 1.
