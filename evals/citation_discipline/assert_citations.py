"""Promptfoo Python assertion: every financial-shape numeric in the answer
carries a `[ec_xxx]` citation drawn from the FactPack.

Aligned with the production parser in `backend/app/chat/citations.py`:
- Only flags decimals (e.g. 2.1, 2.1%), thousands-separated numbers, and
  explicit-percent integers. Plain integers (1, 5, 10), ISO dates, and
  "Month Day, Year" written-out dates are ignored.

Invoked as:

  - type: python
    value: file://citation_discipline/assert_citations.py
"""

from __future__ import annotations

import json
import re
from typing import Any

CITATION_RE = re.compile(r"\[(ec_[a-f0-9]{6,})\]")
# Same shape as backend/app/chat/citations._FINANCIAL_NUMBER_RE.
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


def get_assert(output: str, context: dict[str, Any]) -> dict[str, Any]:
    valid_ids = _collect_fact_pack_ids(context["vars"].get("fact_pack", ""))
    failures: list[str] = []

    cited_ids = set(CITATION_RE.findall(output))
    bad_ids = cited_ids - valid_ids
    if bad_ids:
        failures.append(f"unknown engine_call_ids cited: {sorted(bad_ids)}")

    cited_spans: list[tuple[int, int]] = [
        (max(0, m.start() - LOOKBEHIND_WINDOW), m.start())
        for m in CITATION_RE.finditer(output)
    ]
    iso_dates = [(m.start(), m.end()) for m in ISO_DATE_RE.finditer(output)]
    written_dates = [(m.start(), m.end()) for m in WRITTEN_DATE_RE.finditer(output)]
    skip_ranges = iso_dates + written_dates

    uncited_numerics: list[str] = []
    for m in FINANCIAL_NUMBER_RE.finditer(output):
        if any(start <= m.start() and m.end() <= end for start, end in skip_ranges):
            continue
        if any(start <= m.start() < end for start, end in cited_spans):
            continue
        window_after = output[m.end() : m.end() + LOOKAHEAD_WINDOW]
        if CITATION_RE.search(window_after.split(".")[0]):
            continue
        uncited_numerics.append(m.group(0))
    if uncited_numerics:
        failures.append(f"uncited numerics: {uncited_numerics}")

    if failures:
        return {"pass": False, "score": 0, "reason": "; ".join(failures)}
    return {"pass": True, "score": 1, "reason": "every financial number is cited"}
