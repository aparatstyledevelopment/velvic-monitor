# ADR 0007 — Monorepo with DO App Platform multi-component deploy

**Status:** Accepted, 2026-04-29.

## Context

Backend (Python) and frontend (TypeScript) are independent technically.
Two-repo split is the conventional choice; monorepo is the modern choice for
full-stack apps.

## Decision

Single git repository with `backend/`, `frontend/`, `shared/`, `docs/`,
`evals/` directories. Single Digital Ocean App Platform App with five
components (`web`, `worker`, `frontend`, `db`, `redis`). Deploy spec in
`app.yaml` checked into the monorepo.

## Rationale

Atomic cross-stack PRs eliminate contract drift. Generated TypeScript types
from FastAPI OpenAPI flow trivially in a monorepo. Single CI pipeline. One
person = one context. Monorepo splits to two repos in ~1 day if ever needed;
the reverse is much harder.

## Consequences

CI workflows path-filter so backend changes don't trigger frontend builds and
vice versa. Dependency graphs remain isolated (pyproject.toml in `backend/`,
package.json in `frontend/`).
