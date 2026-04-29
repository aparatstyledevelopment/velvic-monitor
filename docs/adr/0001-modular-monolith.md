# ADR 0001 — Modular monolith over microservices for v1

**Status:** Accepted, 2026-04-29.

## Context

v1 ships the Drivers module with a small team (one senior engineer + AI agent)
over 8–10 weeks. The product has clear long-term modular structure (14 modules)
which suggests a service-oriented architecture might fit eventually.

## Decision

Build v1 as a modular monolith — single Python codebase, single Postgres
database, single deployable artifact — organized internally into bounded
contexts (`crawlers`, `ingestion`, `engine`, `chat`, `pipeline`, `auth`,
`tenancy`, `admin`, `api`). Module boundaries are enforced socially via
per-package `AGENTS.md` and via lint rules forbidding cross-context imports
outside contracts.

## Rationale

Premature microservices cost roughly two engineer-weeks each for
service-to-service auth, distributed tracing, message bus, deployment pipeline,
log aggregation. With one engineer, that overhead burns the runway needed for
product. Modularity inside one process is sufficient until two of three signals
trigger: divergent load profiles, team-coordination tax, or hard
regulatory/security boundaries. None apply at v1.

## Consequences

All cross-module communication is in-process. Easier to refactor early. Future
service extraction is documented as the next architectural step (a future ADR).
Lint rules + `AGENTS.md` prevent informal smuggling of cross-module reads.

## Extraction seams (when the time comes)

- `worker` → its own service (already a separate process).
- `crawlers` + `ingestion` → "data platform" service.
- `chat` orchestrator → its own service.
