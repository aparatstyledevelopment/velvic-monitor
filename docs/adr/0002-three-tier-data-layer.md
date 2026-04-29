# ADR 0002 — Three-tier data layer (raw / curated / derived)

**Status:** Accepted, 2026-04-29.

## Context

Data flows from many heterogeneous external sources (Yahoo, MFN, Riksbank, …)
into the system. Without isolation, source schema drift contaminates business
logic; without normalization, business logic duplicates per-source quirks.

## Decision

Three explicit tiers:

- **Tier 1 raw:** one table per source, schema mirroring upstream, append-only,
  `raw_payload` preserved verbatim.
- **Tier 2 curated:** source-agnostic normalized domain concepts; carries
  `(source, source_row_id)` lineage on every row.
- **Tier 3 derived:** computed insights, materialized, stamped with
  `engine_version`.

Engine code reads Tier 2 and Tier 3 only; never Tier 1. Crawlers write Tier 1
only.

## Rationale

Source-quirk isolation. Lineage preserved. Switching providers (Yahoo →
Millistream) only requires Tier 1 + ingestion changes. Recomputation of
derived facts is deterministic and replayable.

## Consequences

Slightly more storage (raw kept verbatim). Slightly more code (ingestion
transforms). These costs are acceptable given the audit and source-swap
properties gained.
