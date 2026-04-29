# pipeline/AGENTS.md

Celery worker + beat. Orchestrates crawl → ingest → engine briefing chains.

## Discipline

- Pipeline tasks are orchestration only. No business logic — call into
  `crawlers/`, `ingestion/`, `engine/`.
- Idempotent. Each task can be re-run safely.
- Beat schedule lives in `schedules.py`. Schedule changes go through PR review.
- Failed tasks retry with exponential backoff up to 3 times before alerting.
