# ADR 0003 — Engine/Narrator pattern as the LLM contract

**Status:** Accepted, 2026-04-29.

## Context

The product must be trustworthy for compliance-aware IR teams. LLM
hallucinations on numbers are unacceptable.

## Decision

The LLM never produces a number, ticker, ISIN, date, or factual claim from its
own knowledge. Every numerical claim in any rendered output comes from a
deterministic Engine tool result, identified by an `engine_call_id`, persisted
to the `engine_call` ledger, and citable from the rendered text. The LLM's
role is purely linguistic: pick tools, weave results into prose, cite each
numerical claim.

For long-tail questions a typed tool can't answer, an `ad_hoc_query` tool lets
the LLM write SQL against a read-only set of analytical views; the SQL is
AST-validated and executed in a least-privilege Postgres session.

## Rationale

Hallucination becomes structurally impossible (or immediately visible: any
number without a citation is flagged). Auditability for IR teams.
Provider-agnostic — works with any tool-calling LLM. New modules drop in via
the registry, no chat-layer changes.

## Consequences

Engine tool API design is the long-lived interface; we invest in getting it
right. Citation parsing must be robust. Output validation (reject uncited
numerics) is a CI eval gate.
