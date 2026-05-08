"""Promptfoo Python assertion: every distinct financial value in the answer
is cited at least once with a `[ec_xxx]` from the FactPack.

Aligned with backend/app/chat/citations.py for shape (decimals, thousands,
explicit %), but lenient about restatements: if "1.2%" is cited, a later
"1.2 percentage points" is fine. Production stays strict (retries on any
uncited mention) — the eval just guards against fabricated values.
"""

from __future__ import annotations

import json
import re
from typing import Any

CITATION_RE = re.compile(r"\[(ec_[a-f0-9]{6,})\]")
FINANCIAL_NUMBER_RE = re.compile(
    r"(?<!\d)(?:"
    r"\d+\.\d+%?"
    r"|\d{1,3}(?:,\d{3})+(?:\.\d+)?%?"
    r"|\d+%"
    r")(?![A-Za-z0-9])"
)
ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
WRITTEN_DATE_RE = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{1,2}(?:,\s*\d{4})?\b",
    re.IGNORECASE,
)
LOOKBEHIND_WINDOW = 80
LOOKAHEAD_WINDOW = 40


def _normalize_value(num: str) -> str:
    """Strip % and commas so '1.2%' and '1.2' compare equal."""
    return num.rstrip("%").replace(",", "")


def _collect_fact_pack_ids(fact_pack_raw: str) -> set[str]:
    try:
        pack = json.loads(fact_pack_raw)
    except json.JSONDecodeError:
        return set()
    ids: set[str] = set()

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "engine_call_id" and isinstance(v, str):
                    ids.add(v)
                else:
                    _walk(v)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(pack)
    return ids


def _cited_values(output: str) -> set[str]:
    """Distinct numerical values that appear in the lookback window of any
    citation marker. These are the values the model has grounded.
    """
    seen: set[str] = set()
    for marker in CITATION_RE.finditer(output):
        start = max(0, marker.start() - LOOKBEHIND_WINDOW)
        window = output[start : marker.start()]
        for m in FINANCIAL_NUMBER_RE.finditer(window):
            seen.add(_normalize_value(m.group(0)))
    return seen


def get_assert(output: str, context: dict[str, Any]) -> dict[str, Any]:
    valid_ids = _collect_fact_pack_ids(context["vars"].get("fact_pack", ""))
    failures: list[str] = []

    cited_ids = set(CITATION_RE.findall(output))
    bad_ids = cited_ids - valid_ids
    if bad_ids:
        failures.append(f"unknown engine_call_ids cited: {sorted(bad_ids)}")

    cited_value_set = _cited_values(output)
    iso_dates = [(m.start(), m.end()) for m in ISO_DATE_RE.finditer(output)]
    written_dates = [(m.start(), m.end()) for m in WRITTEN_DATE_RE.finditer(output)]
    skip_ranges = iso_dates + written_dates

    uncited_numerics: list[str] = []
    for m in FINANCIAL_NUMBER_RE.finditer(output):
        if any(start <= m.start() and m.end() <= end for start, end in skip_ranges):
            continue
        if _normalize_value(m.group(0)) in cited_value_set:
            continue
        uncited_numerics.append(m.group(0))
    if uncited_numerics:
        failures.append(f"uncited numerics: {uncited_numerics}")

    if failures:
        return {"pass": False, "score": 0, "reason": "; ".join(failures)}
    return {
        "pass": True,
        "score": 1,
        "reason": "every distinct financial value is cited at least once",
    }
