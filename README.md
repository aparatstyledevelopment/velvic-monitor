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
make seed      # five Swedish demo tickers + peer relationships
make backfill  # crawl + ingest + briefings (requires net + ANTHROPIC_API_KEY)
make dev       # docker compose up
```

Frontend on `http://localhost:5173`, backend on `http://localhost:8080`,
Postgres on `:5432`, Redis on `:6379`.

`make backfill` runs the entire EOD chain in-process: nine crawlers →
ingestion (prices / news with dedup / macro) → daily attribution →
briefing card generation with citation-discipline validation. Without an
LLM key it falls back to a mock provider so the pipeline still completes
end-to-end for local smoke tests.

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

## Design system

Browse every primitive and the design tokens (color / spacing / typography /
radii) in **Ladle**, a Vite-native lightweight Storybook alternative:

```
cd frontend
npm install
npm run ladle           # serves at http://localhost:61000
npm run ladle:build     # builds to frontend/build/
```

Toggle the theme (top bar in the Ladle UI) to see how every semantic token
adapts between light and dark. Components in this repo MUST reference
semantic tokens only — see `frontend/AGENTS.md` and ADR 0008.

## Phases

1. **Phase 0 — Spec-first foundations.** Repo + docs + ADRs + scaffolds + auth + CI.
2. **Phase 1 — Crawlers + Engine + EOD pipeline** *(this branch)*. Nine source
   crawlers, three-tier data layer, ten Engine tools + sqlglot-guarded
   ad_hoc_query, briefing composer with citation discipline, Celery EOD chain,
   five demo tickers, briefings API.
3. **Phase 2 — Chat orchestrator + Source ledger.** Multi-LLM tool loop,
   topic gate, streaming, eval gates.
4. **Phase 3 — Three-pane UI.** Demoable end-to-end product.
5. **Phase 4 — Admin panel + onboarding.** New ticker live in <10 minutes.
6. **Phase 5 — Polish + LOI demos.** Three signed letters of intent.

See `docs/PRD.md`, `docs/ARCHITECTURE.md`, and the ADRs in `docs/adr/`.
