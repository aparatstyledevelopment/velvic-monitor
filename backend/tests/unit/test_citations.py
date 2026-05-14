import pytest

from app.chat.citations import (
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
