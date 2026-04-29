# Security

## Threat model (v1)

Ranked by severity:

1. **Cross-tenant data leak.** Postgres RLS + explicit ownership checks at the
   API. Belt-and-braces.
2. **LLM API key exfiltration.** Org-level BYO keys encrypted at rest with
   `pgcrypto`; decrypted in-memory only at provider call time; never logged.
3. **Prompt injection via news content.** Press release bodies and news summaries
   fed to the LLM are wrapped in `<external_content>...</external_content>`
   markers with system-prompt instructions to treat as data only.
4. **SQL injection via `ad_hoc_query`.** sqlglot AST parsing + read-only Postgres
   role + statement timeout (5s) + max-row LIMIT injection.
5. **Brute-force login.** Rate-limited per IP and per email at the API layer
   (Redis-backed). Account lockout after 10 failed attempts in 1 hour;
   admin-resettable.
6. **Session hijacking.** Cookies `Secure; HttpOnly; SameSite=Lax`. JWT signing
   key rotated quarterly; old keys retained for in-flight token verification.
7. **Token-budget exhaustion.** Per-user message rate limits (10/min) + per-org
   daily token budgets prevent runaway/malicious users from exhausting the
   monthly LLM budget.

## Secrets

- **Production:** DO App Platform encrypted env vars.
- **Development:** `.env.local` gitignored; `.env.example` checked in.
- **Rotation:** quarterly for JWT signing key, on-demand for LLM keys, on
  compromise for everything. Playbook in `playbooks/secret-rotation.md`.

## Logging discipline

Structured JSON. PII-aware: emails, IPs, JWT contents NEVER logged at INFO.
Redacted to `user_id` only. Prompts/completions go to Langfuse separately,
with org-level retention controls.

## RLS

`chat_thread`, `chat_turn`, `chat_engine_call`, `org_company_access`, `app_user`
have RLS enabled. Policies use `current_setting('app.current_org_id')`.
Set per session via `SET LOCAL` in `tenancy/middleware.py` at start of every
request.

## ad_hoc_query guardrails

- sqlglot AST: SELECT only. No INSERT/UPDATE/DELETE/DROP/COPY/CALL.
- Allowed views only: `company_v`, `price_bar_v`, `news_item_v`,
  `macro_observation_v`, `peer_relationship_v`.
- No dangerous functions (`pg_read_file`, no extensions).
- LIMIT auto-injected if absent (cap 1000).
- Statement timeout 5 seconds.
- Postgres role `engine_readonly` has SELECT permission only on those views;
  zero access to raw, derived, auth, or chat tables.
