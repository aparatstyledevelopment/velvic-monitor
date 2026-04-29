# Engineering Standards

## Languages

- Backend: Python 3.12. Pydantic v2. SQLAlchemy 2 async.
- Frontend: TypeScript 5+ in strict mode. React 18.

## Type discipline

- Backend: `mypy --strict`. No `Any`. No untyped function. No `# type: ignore`
  without an inline justification comment and a linked issue.
- Frontend: `tsc --noEmit` clean. No `any`. Avoid `unknown` in component props.

## Style

- Python: black (88 cols), ruff for lint + isort. Pre-commit enforces.
- TypeScript: ESLint + Prettier. Pre-commit enforces.

## Commits

Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`,
`build:`, `ci:`. Each PR has a descriptive title and references its spec.

## Errors

- Use typed exceptions in `core/errors.py`. The API layer maps them to HTTP
  status codes. Never let an internal exception leak as a 500.
- Frontend errors at API boundary surface as toast + a Sentry breadcrumb.

## Logging

- Backend: loguru with JSON sink. Always pass structured fields, never f-strings:
  `log.info("event_name", trace_id=..., engine_call_id=..., ...)`.
- PII redacted at INFO. Sensitive payloads (prompts, completions) go to Langfuse,
  never to general logs.

## Tests

- Pytest for backend. Vitest + React Testing Library for frontend. Playwright
  for E2E.
- Coverage gates: 85% on `engine/` and `ingestion/`, 70% on `api/` and `chat/`.
- Property-based tests (Hypothesis) for stateless calculations: returns,
  citation parsing, AST validation.
- Every Engine tool has at least one test exercising edge inputs (null, empty,
  oversized, type-confused).

## Performance

- p95 chat first-token latency: < 1.5s.
- p95 chat completion: < 4s for typed-tool answers.
- p95 briefing read: < 200ms (precomputed).
- p95 quick action mount: < 350ms.

## Database

- Always go through `tenancy/middleware.py` request scope so RLS is set.
- Explicit ownership checks on tenant-scoped resources, even though RLS is on.
- Migrations via Alembic. Always reversible. Test downgrade locally before merging.

## API

- OpenAPI spec is the contract. Generate TS types into `shared/openapi/types.ts`.
- All endpoints under `/api/`. JSON in / JSON out. SSE for chat streaming only.
- Authenticated endpoints require `httpOnly Secure SameSite=Lax` JWT cookie.
