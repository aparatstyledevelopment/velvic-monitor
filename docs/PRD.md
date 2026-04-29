# Product Requirements

Pointer to the v1 blueprint, §2 *Product Vision & Scope*. The canonical PRD lives
there. This file captures only what is unique to the as-built product as it diverges
from the blueprint.

## v1 user

Head of investor relations at a Swedish-listed company on Nasdaq Stockholm Main
Market or First North Growth Market. Small IR team (1–4 people). English-speaking
in their professional context. Working primarily with international institutional
investors.

## v1 success criterion

Three signed letters of intent from real Swedish IR teams after the polish phase.

## v1 scope (binding)

- One module — Drivers. Daily briefing card + chat to drill into facts.
- Sweden only. End-of-day batch.
- Multi-tenant from day one. Postgres RLS for chat data.
- Multi-LLM provider abstraction (Anthropic / OpenAI / Google).
- Three-pane workspace (sidebar / conversation / artifact stack).
- Email/password auth. Admin invites colleagues.
- Persistent chat threads, scoped per user, listed globally in sidebar.
- `/clear`, `/new`, `/help` slash commands only.
- Admin panel for ticker onboarding (<10 min including peer assignment).

## Out of scope for v1

The remaining 13 modules, attach mechanic on cards, full slash command registry,
SSO, marketing site, Bondholder/Uncover/Holdings add-ons, real-time data,
mobile-native app, Swedish-language UI.

## Quality criteria

- Briefings generate without manual intervention every weekday morning.
- Every numerical claim carries a citation that, when clicked, reveals the
  deterministic computation behind it.
- A new pilot company is onboardable by an admin in under 10 minutes.
- Off-topic chat questions get a polite scope refusal — not a generic LLM completion.
- The product looks like the editorial-minimalist design blueprint, not generic shadcn.
