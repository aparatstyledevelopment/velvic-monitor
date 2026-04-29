# Deployment

## Topology

One Digital Ocean App Platform application, five components:

- `web` — FastAPI HTTP service (autoscale 1–3 on CPU 70%).
- `worker` — Celery worker + beat (single instance v1).
- `frontend` — React SPA static site (DO CDN).
- `db` — Managed Postgres 16 (daily backups, PITR within retention).
- `redis` — Managed Redis 7 (1 GB).

Spec: `app.yaml` at repo root.

## Environments

- **staging** — auto-deployed from `main`.
- **production** — manually promoted from a tagged release.
- **local** — Docker Compose with same Postgres + Redis versions.

## Migrations

Alembic runs as the `web` component's `pre_deploy_command`:
```
cd /app && alembic upgrade head
```
Schema is up-to-date before any new code starts serving traffic.

## Rollback

App Platform supports instant rollback to any prior deploy. For
non-reversible migrations (rare; avoid these), playbook documents the
manual steps.

## Backups & DR

- DO Managed Postgres: daily backups, 7-day retention, PITR within window.
- Phase 5 adds nightly `pg_dump` to DO Spaces (compressed, encrypted, 30-day).

## Secrets

Set as encrypted env vars in DO. See `app.yaml` for the catalog. Rotation
playbook in `playbooks/secret-rotation.md`.

## Health checks

`/api/health` returns 200 if process alive + DB reachable + Redis reachable.
DO uses this for liveness probes.

## Runbooks

In `playbooks/`:
- `deploy-and-rollback.md`
- `secret-rotation.md`
- `incident-response.md` (light v1; thickens with experience)
- `manual-briefing-regeneration.md`
- `restore-from-backup.md`
