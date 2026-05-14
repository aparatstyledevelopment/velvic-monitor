"""Suggested follow-up labels emitted with each assistant turn.

Frontend renders these as chips that prefill the composer when clicked.
Per UI spec, labels stay <= 4 words: short enough to scan, the model
answers using the thread context.

The generator is deterministic: it inspects the assistant text and the
engine tool names called this turn, picks up to three labels from a
small library, falls back to a stable cold-start tail.
"""

from __future__ import annotations

from collections.abc import Sequence

# (matcher, label). The matcher receives the lowercased final text plus
# the set of tool names called this turn; first three matches win, in
# declaration order. Labels are <= 4 words.
_LIBRARY: list[tuple[str, str]] = [
    ("price", "Peers today?"),
    ("price", "30-day trend"),
    ("benchmark", "Benchmark this week"),
    ("sector", "Sector laggards"),
    ("peer", "Closest peers"),
    ("news", "Today's regulatory news"),
    ("news", "MAR-flagged items"),
    ("insider", "Insider activity"),
    ("short", "Short interest trend"),
    ("ownership", "Recent buyers"),
    ("attribution", "Attribution breakdown"),
    ("macro", "FX vs SEK"),
]

_DEFAULT_TAIL: list[str] = [
    "Peers today?",
    "MAR-flagged items",
    "Closest peers",
]


def generate(*, final_text: str, tool_names: Sequence[str]) -> list[str]:
    """Return up to three short follow-up labels (<= 4 words each)."""
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
