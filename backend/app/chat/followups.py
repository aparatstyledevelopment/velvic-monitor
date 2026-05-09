"""Suggested follow-up questions emitted with each assistant turn.

The frontend renders these as interactive chips that prefill the composer.
Suggestions are prose questions, not facts — they don't carry numbers and
don't need engine_call_ids, so the engine/narrator contract is unaffected.

Phase-3 ships a deterministic heuristic generator: it inspects the
assistant text and engine_call_ids touched in the turn to pick three
relevant follow-ups from a small library. This keeps cost and latency
flat. Swap to LLM-generated followups by replacing `generate` while
keeping the signature stable.
"""

from __future__ import annotations

from collections.abc import Sequence

# (matcher, candidate). The matcher receives the lowercased final text
# plus the set of tool names called this turn; first three matches win,
# in declaration order. The default tail covers the cold-start case.
_LIBRARY: list[tuple[str, str]] = [
    ("price", "Did peers move similarly today?"),
    ("price", "Show me the 30-day price trend"),
    ("benchmark", "How did the benchmark move this week?"),
    ("sector", "Which sector peers underperformed today?"),
    ("peer", "Compare against the closest peers"),
    ("news", "Summarise today's regulatory news"),
    ("news", "Any MAR-flagged items in the last 30 days?"),
    ("insider", "Any insider activity this week?"),
    ("short", "What's the trend in short interest?"),
    ("ownership", "Who's been buying recently?"),
    ("attribution", "Break down today's relative move"),
    ("macro", "How did FX move against the SEK today?"),
]

_DEFAULT_TAIL: list[str] = [
    "Did peers move similarly today?",
    "Any MAR-flagged news in the last 30 days?",
    "Compare against the closest peers",
]


def generate(*, final_text: str, tool_names: Sequence[str]) -> list[str]:
    """Return up to three short follow-up questions for the given turn.

    Order: first matches against the assistant text, then matches against
    tool names, then a stable cold-start tail. Duplicates collapsed.
    """
    haystack = final_text.lower()
    chosen: list[str] = []
    seen: set[str] = set()

    def take(candidate: str) -> None:
        if candidate in seen:
            return
        chosen.append(candidate)
        seen.add(candidate)

    for needle, candidate in _LIBRARY:
        if len(chosen) >= 3:
            break
        if needle in haystack:
            take(candidate)

    if len(chosen) < 3:
        joined_tools = " ".join(tool_names).lower()
        for needle, candidate in _LIBRARY:
            if len(chosen) >= 3:
                break
            if needle in joined_tools:
                take(candidate)

    for candidate in _DEFAULT_TAIL:
        if len(chosen) >= 3:
            break
        take(candidate)

    return chosen[:3]
