"""Unit tests for the briefing-response JSON extractor and parsing."""

from app.engine.drivers.briefing import (
    _extract_json,
    _parse_briefing_response,
    _round_numerics,
)


def test_extract_plain_json() -> None:
    data = _extract_json('{"narrative": "ok", "smart_chips": ["a"]}')
    assert data["narrative"] == "ok"
    assert data["smart_chips"] == ["a"]


def test_extract_json_in_code_fence() -> None:
    raw = '```json\n{"narrative": "ok", "smart_chips": []}\n```'
    data = _extract_json(raw)
    assert data["narrative"] == "ok"


def test_extract_invalid_json_falls_back() -> None:
    data = _extract_json("this is not JSON")
    assert data["narrative"] == "this is not JSON"
    assert data["smart_chips"] == []


def test_parse_response_with_citations_and_chips() -> None:
    raw = (
        '{"narrative": "VOLV-B closed -2.1% [ec_aaaaaa].", '
        '"smart_chips": ['
        '{"title": "Why?", "prompt": "Why did VOLV-B move?"},'
        '{"title": "Peer compare", "prompt": "How did the peer group fare?"}'
        ']}'
    )
    out = _parse_briefing_response(raw, valid_ids={"ec_aaaaaa"})
    assert out.narrative == "VOLV-B closed -2.1%."
    assert out.smart_chips == [
        {"title": "Why?", "prompt": "Why did VOLV-B move?"},
        {"title": "Peer compare", "prompt": "How did the peer group fare?"},
    ]
    assert not out.has_uncited_numerics


def test_parse_response_upgrades_legacy_string_chips() -> None:
    raw = (
        '{"narrative": "ok", '
        '"smart_chips": ["Did peers move similarly today?"]}'
    )
    out = _parse_briefing_response(raw, valid_ids=set())
    assert len(out.smart_chips) == 1
    chip = out.smart_chips[0]
    assert chip["prompt"] == "Did peers move similarly today?"
    assert len(chip["title"].split()) <= 4
    assert chip["title"]  # non-empty


def test_parse_response_with_uncited_numeric_flagged() -> None:
    raw = '{"narrative": "Return was 2.5%.", "smart_chips": []}'
    out = _parse_briefing_response(raw, valid_ids=set())
    assert out.has_uncited_numerics
    assert out.uncited
    # Smart chips capped at 5 even when more provided.
    raw_many = '{"narrative": "ok", "smart_chips": ["a","b","c","d","e","f","g"]}'
    out2 = _parse_briefing_response(raw_many, valid_ids=set())
    assert len(out2.smart_chips) == 5


def test_round_numerics_trims_decimal_strings_to_4dp() -> None:
    # Regression: Pydantic serialised Decimals with full mantissa, leaving
    # the LLM to copy `-0.61657263969171483622350674371` into prose.
    data = {
        "last_close": "128.949997",
        "daily_return_pct": "-0.61657263969171483622350674371",
        "five_day_history": [{"close": "129.750000", "volume": 1771214}],
    }
    out = _round_numerics(data)
    assert out["last_close"] == "128.9500"
    assert out["daily_return_pct"] == "-0.6166"
    assert out["five_day_history"][0]["close"] == "129.7500"
    # Integers unchanged.
    assert out["five_day_history"][0]["volume"] == 1771214


def test_round_numerics_preserves_non_numeric_strings_and_none() -> None:
    out = _round_numerics(
        {"ticker": "NDA-SE", "name": "Nordea", "sector": None, "items": []}
    )
    assert out == {"ticker": "NDA-SE", "name": "Nordea", "sector": None, "items": []}
