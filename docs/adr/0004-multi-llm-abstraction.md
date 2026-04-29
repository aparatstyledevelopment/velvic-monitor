# ADR 0004 — Multi-LLM provider abstraction

**Status:** Accepted, 2026-04-29.

## Context

The product owner wants the freedom to swap LLM providers per organization
(cost, geography, regulatory preference). Three providers in scope: Anthropic,
OpenAI, Google.

## Decision

A thin internal `LLMProvider` interface (~200 LOC) with three implementations.
Each maps the unified `ToolSpec` to its provider's native tool-call schema and
emits uniform `CompletionEvent` streams. Cost-per-token metadata is part of
the abstraction.

We deliberately avoid larger abstractions like LiteLLM for v1: tool-calling
fidelity matters too much to be one-tier removed from the provider SDKs.

## Rationale

Fits the customer-choice and BYO-key requirements. Three providers' native APIs
are stable enough to wrap directly. Cost transparency enables model tiering and
budget enforcement.

## Consequences

Each new provider is ~150 LOC. We track each provider's API releases.
Provider-specific features (Anthropic prompt caching, OpenAI predicted outputs)
are exposed via optional capabilities on the interface.
