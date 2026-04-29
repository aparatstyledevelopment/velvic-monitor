# ADR 0005 — Source isolation in Tier 1 raw tables

**Status:** Accepted, 2026-04-29. Companion to ADR 0002.

## Context

Multiple sources may publish overlapping data (e.g., MFN + ESAP both serve
regulatory disclosures). Tempting to "blend" at ingest, losing lineage.

## Decision

Each source has its own Tier-1 table. No blending in Tier 1. Deduplication
happens at the Tier-2 ingestion layer with explicit lineage trails
(`also_seen_in`).

## Rationale

Lineage preserved. Source-specific quirks isolated. Ingestion logic is testable
with fixtures per source. Source-swap is a Tier-1 + ingestion swap, not a
schema rewrite.

## Consequences

More tables in Tier 1. Worth it: each crawler tests in isolation; downstream
code never has to know which source a fact came from beyond the `source` column.
