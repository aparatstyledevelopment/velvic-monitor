# AGENTS.md

This is an AI-native monorepo. AI coding agents read this file at the start of every
session. Keep it short. Detailed guidance lives in `docs/`.

## Project

Conversational investor relations workspace for Swedish-listed companies. The first
release ships the Drivers module, which answers "why did our stock move yesterday?"
End-to-end architecture in `docs/ARCHITECTURE.md` (and the v1 blueprint).

## Commands

- `make install` — install backend + frontend deps
- `make dev` — run backend + frontend + worker locally (Docker Compose)
- `make test` — run unit + property + integration tests
- `make evals` — run LLM eval suite (requires API keys)
- `make e2e` — run Playwright E2E
- `make lint` — ruff + black + mypy + tsc + eslint
- `make migrate` — run pending Alembic migrations
- `make build` — production build of frontend
- `make deploy-staging` — push to main (auto-deploys via DO)

## Project structure

- `backend/app/` — FastAPI app, organized by bounded context
  - `crawlers/` — external HTTP, writes Tier-1 raw only
  - `ingestion/` — raw → curated transforms
  - `engine/` — deterministic computation, exposes tools to LLM
  - `chat/` — conversation orchestrator, multi-LLM, citations
  - `pipeline/` — Celery tasks
  - `auth/`, `tenancy/`, `admin/`, `api/` — supporting layers
- `frontend/src/` — React SPA
  - `design/` — tokens + Radix-wrapped primitives
  - `layout/` — app shell, sidebar, top bar, artifact pane
  - `modules/drivers/` — Drivers module surfaces
  - `conversation/`, `artifacts/`, `auth/`, `admin/`
- `docs/` — specs and ADRs
- `evals/` — Promptfoo LLM evals
- `shared/openapi/` — generated OpenAPI spec + TS types

## Code style

- Python 3.12, Pydantic v2, SQLAlchemy 2 async. `mypy --strict`. No `Any`.
  Format: black. Lint: ruff. Imports: isort via ruff.
- TypeScript strict. ESLint + Prettier. No `any`.
- Conventional Commits. Each PR has a descriptive title and references its spec.
- Tests live in `tests/`. Coverage gates: 85% on engine + ingestion, 70% elsewhere.
  Property tests for stateless calculations.
- Every Engine tool has at least one unit test exercising edge inputs (null, empty,
  oversized).

## Boundaries (read these BEFORE writing code that crosses package lines)

- `crawlers/` writes Tier-1 raw only. Never reads curated or derived. No business
  logic. Each crawler subclasses `BaseCrawler`.
- `ingestion/` reads Tier-1 raw, writes Tier-2 curated. No HTTP. No LLM calls.
- `engine/` reads Tier-2 curated and Tier-3 derived. Writes Tier-3 derived and
  the engine_call ledger. Engine tools never call HTTP. The briefing composer in
  `engine/drivers/briefing.py` is the ONLY engine code that may call the LLM.
- `chat/` reads Engine tools via the registry. Never reads raw or curated tables
  directly. Always provider-agnostic — use the `LLMProvider` interface.
- `api/` is thin. Pydantic schemas + dependency-injected services. No business logic.

## The Engine/Narrator contract (HARD RULE)

The LLM never produces a number, ticker, ISIN, person name, or factual claim from
its own knowledge. Every numerical claim cites an `engine_call_id`. If you see a
prompt or tool that lets the LLM "estimate" or "approximate", that is a bug.

## Spec-driven workflow

Non-trivial features start in `docs/specs/<feature>.md`. Specs cover: what it
does, inputs/outputs, edge cases, test cases, success criteria, assumptions.
Reference the spec in your PR. Specs live forever.

## ADR rule

If the change introduces an architectural decision that's hard to reverse
(new dependency, new module pattern, new data tier, new auth approach),
add an ADR in `docs/adr/` numbered sequentially.

## Detailed docs

@docs/PRD.md
@docs/ARCHITECTURE.md
@docs/DATA_MODEL.md
@docs/DATA_SOURCES.md
@docs/ENGINEERING_STANDARDS.md
@docs/PROMPTS.md
@docs/SECURITY.md
@docs/DEPLOYMENT.md
