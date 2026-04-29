# ADR 0008 — Custom design tokens layered on Radix primitives

**Status:** Accepted, 2026-04-29.

## Context

Design blueprint V4 specifies a precise editorial-minimalist aesthetic
incompatible with shadcn defaults. Radix UI provides accessible behavioral
primitives without imposing visual choices.

## Decision

Three-layer token system: primitive (raw values) → semantic (roles) → component
(applications). Components import from semantic tokens only. We use Radix
primitives (Dialog, Dropdown, Tooltip, Popover, etc.) for accessibility — fully
unstyled — and apply our own design-token-grounded classes.

We do NOT use shadcn/ui components directly. shadcn's value (paste-and-customize)
is a small win for components we'd rewrite anyway given the strictness of the
design spec.

## Rationale

The aesthetic blueprint is highly opinionated; achieving it on shadcn defaults
requires more override than greenfield. Radix gives us accessibility for free
without imposing visuals. The token system makes interface-size and
chart-palette switches trivial.

## Consequences

~3 days extra in Phase 0 to build the design system foundation. Every later
phase moves faster because primitives are stable. We commit to maintaining the
token system as the design source of truth.
