# Add a new module

A "module" is a top-level area of the app (Drivers, Shareholders, Stock, etc.).
v1 ships Drivers; the remaining 13 follow this template.

## Steps

1. **Spec.** `docs/specs/module-<name>.md` covering surfaces, tools, briefing
   shape, success criteria.
2. **ADR (if needed).** New external sources, new data tier, new schema → ADR.
3. **Schema.** Alembic migration adding any new Tier-1 / Tier-2 / Tier-3 tables.
4. **Crawler(s).** Subclass `BaseCrawler` in `backend/app/crawlers/<source>.py`.
   One crawler per source. Per-package `AGENTS.md` rules apply.
5. **Ingestion transforms.** `backend/app/ingestion/<topic>.py` reads Tier-1,
   writes Tier-2.
6. **Engine tools.** `backend/app/engine/<module>/tools.py` exposes typed tools
   via `@engine_tool`. Cover edge inputs in tests.
7. **Briefing composer (if module has a briefing).**
   `backend/app/engine/<module>/briefing.py` assembles FactPack + calls Narrator.
   Prompts in `backend/app/engine/<module>/prompts.py`.
8. **Frontend module.** `frontend/src/modules/<name>/<Name>Module.tsx` +
   `BriefingCard.tsx` + quick actions.
9. **Quick actions.** Per-module full-bleed surfaces in
   `frontend/src/modules/<name>/quickActions/`.
10. **Tests.** Unit on tools, property on calculations, integration crawl→ingest
    →engine, eval on briefing prose + citations.
11. **Wire.** Sidebar entry + route + module switcher.

## Discipline

- Tools register themselves; chat orchestrator picks them up automatically.
- No cross-module imports. Shared utilities go in `engine/shared/`.
