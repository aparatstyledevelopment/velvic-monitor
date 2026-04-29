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

## Scope (v1)

- One module — Drivers — for Swedish tickers (Nasdaq Stockholm Main + First North).
- End-of-day batch briefings, generated nightly after market close.
- Multi-tenant from day one with Postgres row-level security.
- Email/password auth; admin invites colleagues.
- Three-pane workspace: sidebar, conversation, artifact stack.

## Status

Implementation in progress. See `Technical_Blueprint_v1.md` for the full architecture, phased plan, and per-component specs.
