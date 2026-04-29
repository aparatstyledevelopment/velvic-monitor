# Architecture

Pointer to the v1 blueprint, §3 *System Architecture* and §4 *Engine / Narrator
Pattern*. Binding architectural decisions are also captured as ADRs in `adr/`.

## One-line summary

Modular monolith on Python 3.12 / FastAPI / Postgres / Redis / Celery, served
alongside a React / TypeScript / Vite SPA, deployed as one Digital Ocean App
Platform application with five components.

## Bounded contexts

| Package | Reads from | Writes to | Calls LLM? | Calls HTTP? |
|---|---|---|---|---|
| `crawlers/` | external | Tier-1 raw | no | yes |
| `ingestion/` | Tier-1 | Tier-2 curated | no | no |
| `engine/` | Tier-2, Tier-3 | Tier-3 derived, `engine_call` ledger | only `engine/drivers/briefing.py` | no |
| `chat/` | Engine tools (via registry) | `chat_thread`, `chat_turn`, `chat_engine_call` | yes (provider-agnostic) | only LLM providers |
| `pipeline/` | n/a (orchestration) | n/a | no | no |
| `auth/`, `tenancy/` | own tables | own tables | no | no |
| `admin/` | own tables, Tier-1 | own tables | no | yes (peer-suggest helpers) |
| `api/` | services | services | no | no |

These boundaries are enforced socially (per-package `AGENTS.md`) and via lint rules
(e.g., `engine/` may not import `requests` or `httpx`).

## The Engine/Narrator contract

The keystone. The LLM never produces a number, ticker, ISIN, person name, or date
from its own knowledge. Every numerical claim in any rendered output is the result
of a deterministic Engine tool call, identified by an `engine_call_id`, persisted
to the `engine_call` ledger, citable from the rendered text. Citation parsing and
output validation are non-bypassable.

## Three-tier data layer

Tier-1 raw (per-source) → Tier-2 curated (source-agnostic) → Tier-3 derived
(materialized computations). Engine reads Tier-2 and Tier-3 only. See
`DATA_MODEL.md`.

## Future service-extraction seams

When two of three signals trigger (divergent load profiles, team-coordination tax,
hard regulatory boundary), the natural splits are:
- `worker` → its own service.
- `crawlers` + `ingestion` → "data platform" service.
- `chat` orchestrator → its own service.

None are needed for v1.
