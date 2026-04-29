# Data Model

Canonical schema is the live Alembic migrations under
`backend/alembic/versions/`. The blueprint Appendix C carries the full DDL with
indexes and RLS policies.

## Three tiers

- **Tier 1 — Raw.** One table per source, schema mirrors upstream. Append-only
  with `superseded_by` linkage. `raw_payload jsonb` preserved verbatim.
- **Tier 2 — Curated.** Source-agnostic, normalized. Idempotent upserts keyed on
  `(source, source_row_id)`. Lineage carried on every row.
- **Tier 3 — Derived.** Computed insights. Materialized. Stamped with
  `engine_version`. Recomputable from curated inputs.

## Tenancy

Global facts about Swedish-listed companies are NOT tenant-scoped (`company`,
`price_bar`, `news_item`, `macro_observation`, `daily_attribution`,
`briefing_card`). Tenant scoping applies to access (`org_company_access`), chat
(`chat_thread`, `chat_turn`, `chat_engine_call`), and billing.

Postgres row-level security enforces isolation on tenant-scoped tables.
`app.current_org_id` is set per session via `SET LOCAL` in the SQLAlchemy
session middleware.

## Engine call ledger

Every Engine tool invocation persists one row in `engine_call`:
`(id, tool_name, module, params, result, source_refs, status, latency_ms,
engine_version, called_at)`. `id` is content-addressed:
`hash(tool_name + canonical_params + as_of_date)`. Calls are reused across users
in the same org via this hash.

## Migrations

Alembic. Every migration must be tested with both upgrade and downgrade. PRs
that change schema include a migration; CI runs `alembic upgrade head` against
a fresh test database.

`engine_version` is a build-time string injected at deploy. Tier-3 derived rows
carry it so we can identify which version of the calculation logic produced a row,
and re-derive when logic changes.
