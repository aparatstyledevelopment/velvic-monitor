"""Promptfoo Python assertion: every numeric in the answer carries a `[ec_xxx]`
citation drawn from the FactPack. Invoked as:

  - type: python
    value: file://citation_discipline/assert_citations.py
"""

from __future__ import annotations

import json
import re
from typing import Any

CITATION_RE = re.compile(r"\[(ec_[a-f0-9]{6,})\]")
NUMBER_RE = re.compile(r"\b\d+(?:[.,]\d+)?%?(?![A-Za-z0-9])")
LOOKBEHIND_WINDOW = 80


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

    cited_spans: list[tuple[int, int]] = []
    for m in CITATION_RE.finditer(output):
        cited_spans.append((max(0, m.start() - LOOKBEHIND_WINDOW), m.start()))

    uncited_numerics: list[str] = []
    for m in NUMBER_RE.finditer(output):
        in_year = re.match(r"^\d{4}$", m.group(0)) and 1900 < int(m.group(0)) < 2100
        if in_year:
            continue
        if not any(start <= m.start() < end for start, end in cited_spans):
            window_after = output[m.end() : m.end() + 40]
            if not CITATION_RE.search(window_after.split(".")[0]):
                uncited_numerics.append(m.group(0))
    if uncited_numerics:
        failures.append(f"uncited numerics: {uncited_numerics}")

    if failures:
        return {"pass": False, "score": 0, "reason": "; ".join(failures)}
    return {"pass": True, "score": 1, "reason": "every numeric is cited"}
