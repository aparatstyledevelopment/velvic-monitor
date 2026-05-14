import pytest

from app.chat.citations import (
    auto_ground,
    build_values_index,
    find_uncited_numerics,
    parse_citations,
)


def test_parses_single_citation_and_strips_marker() -> None:
    text = "VOLV-B closed -2.1% [ec_8f3a3b]."
    valid = {"ec_8f3a3b"}
    result = parse_citations(text, valid)
    assert result.text == "VOLV-B closed -2.1%."
    assert len(result.spans) == 1
    span = result.spans[0]
    assert span.engine_call_id == "ec_8f3a3b"
    # The cited fragment is "-2.1%"; the start_char locates "2.1%"-shaped match.
    cited = result.text[span.start_char : span.end_char]
    assert cited.endswith("%")
    assert "2.1" in cited


def test_multiple_citations_share_text() -> None:
    text = "VOLV-B closed -2.1% [ec_aaaaaa] vs OMX -0.4% [ec_bbbbbb]."
    result = parse_citations(text, {"ec_aaaaaa", "ec_bbbbbb"})
    assert "[ec_" not in result.text
    assert len(result.spans) == 2
    assert {s.engine_call_id for s in result.spans} == {"ec_aaaaaa", "ec_bbbbbb"}


def test_unknown_citation_id_is_dropped_not_raised() -> None:
    # An unknown hex-shaped id is logged + dropped rather than raised:
    # one fabricated citation must not break the whole turn.
    result = parse_citations("close 1.2% [ec_deadbeef]", {"ec_cafebabe"})
    assert "[ec_deadbeef]" not in result.text
    assert "1.2%" in result.text
    assert result.spans == []


def test_uncited_numeric_detected() -> None:
    text = "Return was 2.5% versus 1.0%."
    result = parse_citations(text, set())
    uncited = find_uncited_numerics(result.text, result.spans)
    assert any("2.5" in u[2] for u in uncited)
    assert any("1.0" in u[2] for u in uncited)


def test_only_cited_numerics_are_clean() -> None:
    text = "Return -2.1% [ec_aaaaaa]."
    result = parse_citations(text, {"ec_aaaaaa"})
    uncited = find_uncited_numerics(result.text, result.spans)
    assert uncited == []


# --------------------------------------------------------------------------
# Deterministic grounder (build_values_index + auto_ground)
# --------------------------------------------------------------------------


def test_build_values_index_canonicalises_percent_and_decimal_forms() -> None:
    index = build_values_index(
        [
            ("ec_aaaaaa", {"last_close": 167.90, "daily_return_pct": -0.62}),
            ("ec_bbbbbb", {"daily_return_pct": 0.16}),
        ]
    )
    # 2dp and 1dp decimal forms emitted for every numeric leaf
    assert "167.90" in index
    assert "167.9" in index
    assert index["167.90"] == {"ec_aaaaaa"}
    # Percent-suffixed forms for return-like values
    assert "0.62" in index
    assert "0.62%" in index
    assert index["0.62%"] == {"ec_aaaaaa"}
    assert index["0.16%"] == {"ec_bbbbbb"}


def test_build_values_index_collapses_identical_values_across_calls() -> None:
    # Same value (-0.62%) appears in both price_move and peer_returns.
    index = build_values_index(
        [
            ("ec_aaaaaa", {"daily_return_pct": -0.62}),
            ("ec_bbbbbb", {"peers": [{"daily_return_pct": -0.62}]}),
        ]
    )
    assert index["0.62%"] == {"ec_aaaaaa", "ec_bbbbbb"}


def test_build_values_index_skips_shadow_keys() -> None:
    # Keys starting with "_" (e.g. _engine_call_id) are bookkeeping, not source values.
    index = build_values_index(
        [("ec_aaaaaa", {"_engine_call_id": "ec_aaaaaa", "value": 1.23})]
    )
    assert "1.23" in index
    # The ec_id string itself should not have been treated as a numeric leaf.
    assert all(not k.startswith("ec_") for k in index)


def test_build_values_index_emits_thousands_separator_for_volumes() -> None:
    index = build_values_index([("ec_aaaaaa", {"volume": 1770546})])
    assert "1,770,546" in index


def test_auto_ground_inserts_marker_for_unique_match() -> None:
    parsed = parse_citations("NDA-SE closed at 167.90 on Tuesday.", set())
    index = {"167.90": {"ec_aaaaaa"}}
    out = auto_ground(parsed, index, {"ec_aaaaaa"})
    # Marker is stripped on re-parse; text remains the same as parsed.text
    assert out.text == parsed.text
    assert len(out.spans) == 1
    assert out.spans[0].engine_call_id == "ec_aaaaaa"
    cited = out.text[out.spans[0].start_char : out.spans[0].end_char]
    assert "167.9" in cited


def test_auto_ground_leaves_ambiguous_values_uncited() -> None:
    parsed = parse_citations("Swedbank fell 0.62%.", set())
    index = {"0.62%": {"ec_aaaaaa", "ec_bbbbbb"}}  # two candidates
    out = auto_ground(parsed, index, {"ec_aaaaaa", "ec_bbbbbb"})
    # No insertion when source is ambiguous.
    assert out.spans == []
    uncited = find_uncited_numerics(out.text, out.spans)
    assert any("0.62" in u[2] for u in uncited)


def test_auto_ground_preserves_existing_spans() -> None:
    parsed = parse_citations(
        "Nordea -0.62% [ec_aaaaaa] vs OMX +0.16%.", {"ec_aaaaaa", "ec_bbbbbb"}
    )
    # 0.16% should ground to ec_bbbbbb; 0.62% already cited.
    index = {"0.16%": {"ec_bbbbbb"}, "0.62%": {"ec_aaaaaa"}}
    out = auto_ground(parsed, index, {"ec_aaaaaa", "ec_bbbbbb"})
    assert out.text == parsed.text
    ec_ids = {s.engine_call_id for s in out.spans}
    assert ec_ids == {"ec_aaaaaa", "ec_bbbbbb"}


def test_auto_ground_noop_when_no_uncited() -> None:
    parsed = parse_citations("Return -2.1% [ec_aaaaaa].", {"ec_aaaaaa"})
    index = {"2.10%": {"ec_aaaaaa"}}
    out = auto_ground(parsed, index, {"ec_aaaaaa"})
    assert out is parsed  # short-circuit


def test_auto_ground_ignores_match_to_invalid_ec_id() -> None:
    parsed = parse_citations("Close 167.90 today.", set())
    # Index claims a source, but the orchestrator hasn't validated that ec_id.
    out = auto_ground(parsed, {"167.90": {"ec_unknown"}}, valid_ec_ids=set())
    assert out.spans == []
    assert "167.90" in out.text
