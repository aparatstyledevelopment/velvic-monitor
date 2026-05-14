"""Citation marker parsing.

Output discipline: every numerical claim must be followed by a citation
marker `[ec_xxxxxx]` referencing a known engine_call_id. The parser
extracts spans and validates ids against an allow-list. The validator
flags numerics not covered by a citation.

Layered defense:
- `parse_citations` strips markers and yields spans (existing).
- `find_uncited_numerics` regex-flags financial numbers with no marker
  (existing).
- `build_values_index` + `auto_ground` deterministically inject markers
  for uncited numbers whose value is unambiguous across the available
  engine results. The model still owns disambiguation when the same
  value appears in two calls (e.g. `-0.62%` shared by `price_move` and
  `peer_returns`); those remain uncited.

This module is shared between the chat orchestrator (Phase 2) and the
briefing composer (Phase 1).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

from app.core.logging import logger

# Match the marker plus a single optional leading whitespace so the
# rendered text doesn't carry an orphan space before punctuation.
CITATION_RE = re.compile(r"[ \t]?\[(?P<id>ec_[a-f0-9]{6,})\]")
# `\b...\b` would exclude the trailing `%` because `%` isn't a word char;
# negative lookahead for alphanumerics keeps `2.1%` matched whole while
# still rejecting `2.5km`. Multi-comma numbers like `2,189,729` must match
# whole — without the `(?:,\d{3})*` clause the backward-walk would lock onto
# the trailing 3-digit chunk and emit a span over `729` only, leaving the
# real number flagged as uncited.
NUMBER_RE = re.compile(
    r"(?:"
    r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?%?"   # thousands-separated (multi-comma OK)
    r"|\b\d+(?:\.\d+)?%?"                  # plain integer or decimal
    r")(?![A-Za-z0-9])"
)
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
    nearest preceding number-shaped token. Markers referencing an
    unknown id are dropped from the output (the trailing number stays
    visible) and logged — never raised — because a single fabricated
    marker should not break the whole turn.

    Identical spans (same start/end/ec_id) are deduped — a model that
    repeats the same `[ec_xxx]` marker after a value shouldn't render two
    overlapping chips.

    Span offsets are translated from original-text coordinates into
    output-text coordinates by subtracting the length of every prior
    marker whose end falls strictly before the cited fragment's start.
    The naive "cumulative consumed so far" would over-subtract when a
    later marker points BACK at an earlier number (the duplicate-marker
    case).
    """
    spans: list[CitationSpan] = []
    seen: set[tuple[int, int, str]] = set()
    out_chars: list[str] = []
    prev_markers: list[tuple[int, int]] = []
    pos = 0
    for m in CITATION_RE.finditer(text):
        out_chars.append(text[pos : m.start()])
        ec_id = m.group("id")
        if ec_id not in valid_ids:
            logger.warning("parse_citations_unknown_id", engine_call_id=ec_id)
            prev_markers.append((m.start(), m.end()))
            pos = m.end()
            continue
        cited = _find_cited_fragment(text, m.start())
        if cited is not None:
            frag_start, frag_end = cited
            shift = sum(e - s for s, e in prev_markers if e <= frag_start)
            key = (frag_start - shift, frag_end - shift, ec_id)
            if key not in seen:
                seen.add(key)
                spans.append(
                    CitationSpan(
                        start_char=key[0],
                        end_char=key[1],
                        engine_call_id=ec_id,
                    )
                )
        prev_markers.append((m.start(), m.end()))
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


# ----------------------------------------------------------------------------
# Deterministic grounder
# ----------------------------------------------------------------------------


def build_values_index(
    sources: Iterable[tuple[str, Any]],
) -> dict[str, set[str]]:
    """Map canonical numeric forms → set of engine_call_ids that produced them.

    `sources` is `(engine_call_id, payload)` pairs; payload is any
    JSON-able structure (a `data` dict from an engine envelope, a Pydantic
    model dump, etc.). Each numeric leaf is normalised to every string
    form `_FINANCIAL_NUMBER_RE` might capture for it (2dp and 1dp,
    percent-suffixed, and thousands-separated for integers ≥1000). Keys
    starting with `_` are skipped (they're shadow markers, not source
    values).
    """
    out: dict[str, set[str]] = {}
    for ec_id, payload in sources:
        for form in _walk_numerics(payload):
            out.setdefault(form, set()).add(ec_id)
    return out


def auto_ground(
    parsed: ParseResult,
    values_index: dict[str, set[str]],
    valid_ec_ids: set[str],
) -> ParseResult:
    """Inject `[ec_xxx]` markers for uncited numerics with a unique source.

    Numbers whose canonical form appears under exactly one engine_call_id
    in `values_index` get a citation inserted; collisions are left
    uncited so the regex validator can flag them and trigger a strict
    retry. No-op when there are no uncited numerics or no unique matches.
    """
    uncited = find_uncited_numerics(parsed.text, parsed.spans)
    if not uncited:
        return parsed

    inserts: list[tuple[int, str]] = []
    for _start, end, value in uncited:
        candidates = values_index.get(value)
        if candidates is None or len(candidates) != 1:
            continue
        ec_id = next(iter(candidates))
        if ec_id not in valid_ec_ids:
            continue
        inserts.append((end, ec_id))

    if not inserts:
        return parsed

    inserts.sort(key=lambda x: x[0], reverse=True)
    marked = parsed.text
    for pos, ec_id in inserts:
        marked = f"{marked[:pos]} [{ec_id}]{marked[pos:]}"

    reparsed = parse_citations(marked, valid_ec_ids)
    combined_spans = list(parsed.spans) + list(reparsed.spans)
    combined_spans.sort(key=lambda s: (s.start_char, s.end_char))
    return ParseResult(text=reparsed.text, spans=combined_spans)


def _walk_numerics(node: Any) -> Iterator[str]:
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(k, str) and k.startswith("_"):
                continue
            yield from _walk_numerics(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk_numerics(v)
    elif isinstance(node, bool) or node is None:
        return
    elif isinstance(node, (int, float)):
        yield from _canonical_forms(float(node))
    elif isinstance(node, str):
        # Decimals come through model_dump(mode="json") as strings;
        # parse if shaped like a number, otherwise skip.
        try:
            yield from _canonical_forms(float(node))
        except ValueError:
            return


def _canonical_forms(value: float) -> Iterator[str]:
    """Emit every string form `_FINANCIAL_NUMBER_RE` might capture for `value`.

    The regex strips leading sign, so we always canonicalise to abs(value).
    Covers 1-4 decimal places because the FactPack rounds to 4dp before
    the model sees it; the model may also paraphrase down to fewer digits.
    """
    a = abs(value)
    for digits in (1, 2, 3, 4):
        yield f"{a:.{digits}f}"
        yield f"{a:.{digits}f}%"
    if a == int(a) and a >= 1000:
        yield f"{int(a):,}"
