# Velvic Monitor

An AI-native investor relations workspace for Swedish-listed companies.

## What this is

A conversational IR platform that answers the question every IR director asks every morning: *why did our stock move yesterday?* The first release ships the **Drivers module** — a daily briefing card connecting regulatory data, market data, and central-bank macro into a coherent narrative, plus a chat that lets users drill into any number with full provenance.

## Architectural commitment

**Numbers from the engine, narrative from the LLM.** The LLM never produces a number, ticker, date, or named entity from its own knowledge. Every numerical claim is the output of a deterministic Engine call, logged to a content-addressed ledger, citable from the conversation, and inspectable in the right-pane artifact stack.

## Stack

- **Backend:** Python 3.12 / FastAPI / SQLAlchemy 2 async / Pydantic v2
- **Data:** Postgres 16 / Redis 7 / Celery 5
- **Frontend:** React 18 / TypeScript / Vite / Tailwind / Radix UI
- **LLM:** multi-provider (Anthropic / OpenAI / Google), per-org switchable
- **Deploy:** Digital Ocean App Platform, single app, five components

## Repository

```
backend/    FastAPI app, bounded contexts, Alembic migrations, tests
frontend/   React + Vite SPA, design tokens, primitives, App shell
shared/     OpenAPI contract — generated spec.json + types.ts
evals/      Promptfoo LLM eval suites
docs/       Specs, ADRs, playbooks, engineering standards
.github/    backend-ci, frontend-ci, evals, e2e workflows
app.yaml    DO App Platform spec (5 components: web/worker/frontend/db/redis)
```

Each top-level package has its own `AGENTS.md` describing local conventions
for AI coding agents and humans.

## Local development

```
cp .env.example .env.local
make install   # backend + frontend deps
make migrate   # apply Alembic migrations
make dev       # docker compose up
```

Frontend on `http://localhost:5173`, backend on `http://localhost:8080`,
Postgres on `:5432`, Redis on `:6379`.

## Make targets

| Target | What it does |
|---|---|
| `make install` | install backend + frontend deps |
| `make dev` | run backend + worker + frontend + db + redis (compose) |
| `make test` | unit + property + integration |
| `make e2e` | Playwright |
| `make lint` | ruff + black --check + mypy + eslint + tsc |
| `make migrate` | `alembic upgrade head` |
| `make evals` | Promptfoo eval suite (requires API keys) |
| `make build` | production build of frontend |

## Phases

1. **Phase 0 — Spec-first foundations** *(this branch)*. Repo + docs + ADRs +
   scaffolds + auth + CI.
2. **Phase 1 — Crawlers + Engine + EOD pipeline.** Nightly briefing rows for
   five demo tickers.
3. **Phase 2 — Chat orchestrator + Source ledger.** Multi-LLM, citation
   discipline, eval gates.
4. **Phase 3 — Three-pane UI.** Demoable end-to-end product.
5. **Phase 4 — Admin panel + onboarding.** New ticker live in <10 minutes.
6. **Phase 5 — Polish + LOI demos.** Three signed letters of intent.

See `docs/PRD.md`, `docs/ARCHITECTURE.md`, and the ADRs in `docs/adr/`.
