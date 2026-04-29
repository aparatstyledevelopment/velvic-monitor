# CLAUDE.md

Claude-specific extensions to `AGENTS.md`. Read AGENTS.md first.

## Thinking budget

Use extended thinking when:
- Designing or modifying anything in `engine/` (deterministic contract is sacred).
- Touching prompts in `docs/PROMPTS.md` or `engine/drivers/prompts.py`.
- Working across module boundaries.
- Resolving merge conflicts in migrations.

## Slash commands this project supports

- `/review` — review the pending changes on the current branch.
- `/security-review` — security pass over pending changes.
- `/init` — refresh CLAUDE.md from the codebase (rare; ask first).

## Skills to invoke proactively

- `simplify` — after writing a feature, before committing, scan for over-abstraction
  and dead code.
- `claude-api` — when modifying anything in `chat/providers/anthropic.py` or
  prompt-caching logic.

## When to spawn subagents

- `Explore` — for codebase questions touching ≥3 files.
- `Plan` — before implementing any change to `engine/`, `chat/orchestrator.py`,
  or the migration schema. Output the plan; let me approve before coding.
- `general-purpose` — for cross-cutting refactors.

## House rules

- Keep AGENTS.md short. New rules go into the per-package AGENTS.md or into `docs/`.
- Never write a comment that explains *what* the code does. Only *why*, and only
  when non-obvious.
- Never add backwards-compat shims. We're pre-LOI. Change the code.
- Never bypass `mypy --strict` or `tsc --noEmit`. Fix the type, don't `# type: ignore`.
- If a test is flaky, quarantine it with `@pytest.mark.flaky` and file a fix issue,
  do not delete or skip silently.
- For UI work: actually run the dev server and click through the change before
  declaring done. Type-checks alone do not verify UX.
