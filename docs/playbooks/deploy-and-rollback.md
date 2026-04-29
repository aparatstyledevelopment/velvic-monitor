# Deploy and rollback

## Deploy to staging

Push to `main`. DO App Platform auto-deploys all five components. Monitor the
deploy log; the `web` component runs `alembic upgrade head` as its
`pre_deploy_command` before serving traffic.

## Promote to production

1. Cut a release tag: `git tag v0.X.0 && git push --tags`.
2. In DO App Platform UI, manually deploy the production app from the tag.
3. Monitor `/api/health` until green.
4. Smoke-test: log in as the smoke-test user; load a briefing; ask one chat
   question; verify a citation resolves.

## Rollback

1. DO App Platform → App → Deployments → Rollback to the prior deploy. Instant.
2. If the rollback skipped a migration, restore the schema:
   ```
   cd backend && alembic downgrade <prior_revision>
   ```
   Only necessary for forward-incompatible migrations (rare; we should avoid
   these). For most schema changes, the prior code works against the newer
   schema and no downgrade is needed.
3. Post-mortem: write up what failed in `docs/postmortems/YYYY-MM-DD-<slug>.md`.
   Update this playbook if the failure mode is generalizable.

## Forbidden

- `git push --force` to `main`. Ever.
- Editing migrations after they ship. Always add a new migration.
- Hot-patching production env vars without a corresponding commit.
