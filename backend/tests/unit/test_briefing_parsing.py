"""Unit tests for the briefing-response JSON extractor and parsing."""

from app.engine.drivers.briefing import _extract_json, _parse_briefing_response


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
