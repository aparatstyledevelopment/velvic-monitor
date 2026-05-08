"""Citation marker parsing.

Output discipline: every numerical claim must be followed by a citation
marker `[ec_xxxxxx]` referencing a known engine_call_id. The parser
extracts spans and validates ids against an allow-list. The validator
flags numerics not covered by a citation.

This module is shared between the chat orchestrator (Phase 2) and the
briefing composer (Phase 1).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Match the marker plus a single optional leading whitespace so the
# rendered text doesn't carry an orphan space before punctuation.
CITATION_RE = re.compile(r"[ \t]?\[(?P<id>ec_[a-f0-9]{6,})\]")
# `\b...\b` would exclude the trailing `%` because `%` isn't a word char;
# negative lookahead for alphanumerics keeps `2.1%` matched whole while
# still rejecting `2.5km`.
NUMBER_RE = re.compile(r"\b\d+(?:[.,]\d+)?%?(?![A-Za-z0-9])")
# Stricter pattern used by the uncited-numeric check: only flag tokens that
# look like financial values (decimal, thousands-separated, or with %).
# This avoids false positives on list bullets like `1.` `2.`, single-digit
# durations ("5 days"), and ISO dates ("2026-04-30").
_FINANCIAL_NUMBER_RE = re.compile(
    r"(?<!\d)(?:"
    r"\d+\.\d+%?"
    r"|\d{1,3}(?:,\d{3})+(?:\.\d+)?%?"
    r"|\d+%"
    r")(?![A-Za-z0-9])"
)
_ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


@dataclass(frozen=True)
class CitationSpan:
    start_char: int
    end_char: int
    engine_call_id: str


@dataclass(frozen=True)
class ParseResult:
    text: str
    spans: list[CitationSpan]


def parse_citations(text: str, valid_ids: set[str]) -> ParseResult:
    """Extract citation markers, return rendered text + structured spans.

    Each marker `[ec_xxx]` is consumed; the substring it cites is the
    nearest preceding number-shaped token. Unknown ids raise ValueError.
    """
    spans: list[CitationSpan] = []
    out_chars: list[str] = []
    consumed = 0
    pos = 0
    for m in CITATION_RE.finditer(text):
        # Append everything up to the marker (translating offsets).
        out_chars.append(text[pos : m.start()])
        ec_id = m.group("id")
        if ec_id not in valid_ids:
            raise ValueError(f"unknown engine_call_id: {ec_id}")
        cited = _find_cited_fragment(text, m.start())
        if cited is not None:
            frag_start, frag_end = cited
            # Translate to output coordinates by subtracting consumed marker chars.
            spans.append(
                CitationSpan(
                    start_char=frag_start - consumed,
                    end_char=frag_end - consumed,
                    engine_call_id=ec_id,
                )
            )
        consumed += m.end() - m.start()
        pos = m.end()
    out_chars.append(text[pos:])
    return ParseResult(text="".join(out_chars), spans=spans)


def _find_cited_fragment(text: str, marker_start: int) -> tuple[int, int] | None:
    """Return (start, end) of the cited fragment immediately before the marker.

    Heuristic: search backward up to 60 chars for a number-shape; if none,
    return None (the citation will still be persisted, just without a span).
    """
    window = text[max(0, marker_start - 60) : marker_start].rstrip()
    if not window:
        return None
    matches = list(NUMBER_RE.finditer(window))
    if not matches:
        return None
    last = matches[-1]
    return (
        max(0, marker_start - 60) + last.start(),
        max(0, marker_start - 60) + last.end(),
    )


def find_uncited_numerics(
    text: str, spans: list[CitationSpan]
) -> list[tuple[int, int, str]]:
    """Return financial-number substrings in `text` not covered by any span.

    Uses the stricter `_FINANCIAL_NUMBER_RE` so list bullets, single-digit
    durations, and ISO dates aren't flagged as uncited. ISO dates are also
    skipped explicitly even if they happened to match.
    """
    covered: list[tuple[int, int]] = [(s.start_char, s.end_char) for s in spans]
    iso_dates = [(m.start(), m.end()) for m in _ISO_DATE_RE.finditer(text)]
    out: list[tuple[int, int, str]] = []
    for m in _FINANCIAL_NUMBER_RE.finditer(text):
        if any(start <= m.start() and m.end() <= end for start, end in covered):
            continue
        if any(start <= m.start() and m.end() <= end for start, end in iso_dates):
            continue
        out.append((m.start(), m.end(), m.group(0)))
    return out
