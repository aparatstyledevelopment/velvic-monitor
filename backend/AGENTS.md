# Backend AGENTS.md

Local rules for backend code. Inherits from root `AGENTS.md`.

## Stack

Python 3.12 / FastAPI / SQLAlchemy 2 async / Pydantic v2 / Postgres 16 / Redis /
Celery 5.

## Async discipline

All I/O is async. SQLAlchemy session uses `AsyncSession`. HTTP via
`httpx.AsyncClient`. Celery tasks are sync (Celery doesn't fully support async);
when a task needs async code, wrap with `asyncio.run`.

## Errors

Use typed exceptions in `core/errors.py`. The API layer maps them to HTTP
status codes. Never let an internal exception leak as a 500.

## Logging

Loguru. Always pass structured fields, never f-strings:
`log.info("event_name", trace_id=..., engine_call_id=..., ...)`.

## Database access

- Always go through `tenancy/middleware.py` request scope so RLS is set.
- Explicit ownership checks on tenant-scoped resources, even though RLS is on.
- Migrations via Alembic. Always reversible. Test downgrade locally before merging.

## Testing

`pytest -q` for fast iteration. `pytest --cov` enforces gates.
Hypothesis for stateless calc; integration for crawl→ingest→engine.
Postgres test fixtures via Docker Compose service.
