# ADR 0006 — Spec-driven development workflow

**Status:** Accepted, 2026-04-29.

## Context

Most code in v1 will be AI-authored or AI-assisted. AI coding agents drift
without explicit specifications.

## Decision

Every non-trivial feature begins as a markdown spec in `docs/specs/<feature>.md`
covering: what it does, inputs/outputs, edge cases, test cases, success
criteria, explicit assumptions. Specs are reviewed by humans before code
generation. PRs reference the spec. Specs live forever.

## Rationale

Spec-first compresses build time substantially (industry data: ~3–7x on
greenfield work) by reducing AI rework. Specs become the historical record of
design intent. They also serve as the test-case source for evals.

## Consequences

A small upfront cost per feature (~30–60 min of spec writing). Recovers itself
many times over. Specs also act as the canonical onboarding doc for new
contributors and AI sessions.
