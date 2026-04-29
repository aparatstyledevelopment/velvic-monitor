# Secret rotation

## Schedule

- **JWT signing key:** quarterly. Old key retained one rotation cycle to verify
  in-flight tokens.
- **Encryption key (pgcrypto):** quarterly, with a re-encryption pass over
  `org.llm_api_key_enc`.
- **LLM API keys (shared infra):** on-demand; immediately on suspected compromise.
- **DB password, Redis password:** on-demand; rotated through DO Managed UI.

## Procedure (JWT signing key)

1. Generate new key:
   ```
   openssl rand -hex 32
   ```
2. Add as `JWT_SECRET_NEXT` in DO encrypted env vars (do not remove the current
   `JWT_SECRET` yet).
3. Deploy the change. The verifier accepts both the current and `_NEXT` keys.
4. After 24 hours (longer than the longest-lived refresh token's grace),
   promote `_NEXT` to `JWT_SECRET` and remove the old.

## Procedure (LLM API keys, shared infra)

1. Issue new key in the provider console.
2. Update DO env var.
3. Restart `web` and `worker` components.
4. Revoke old key in the provider console.

## On compromise

Rotate immediately, then audit:
- `engine_call` ledger for unusual spikes.
- `chat_turn` aggregate token usage per org.
- Provider dashboard for anomalous spend.
