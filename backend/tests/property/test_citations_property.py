"""Property tests for citation parsing.

Properties: parsing is total over arbitrary text + a known id set,
markers always strip, and a fully-cited input has zero uncited numerics.
"""
from hypothesis import given, settings
from hypothesis import strategies as st

from app.chat.citations import find_uncited_numerics, parse_citations


text_chunks = st.text(
    alphabet="abcdefgh ABCDEFGH 0123456789.%- \n",
    min_size=0,
    max_size=80,
)


@given(text=text_chunks)
@settings(max_examples=50, deadline=None)
def test_no_markers_no_spans(text: str) -> None:
    result = parse_citations(text, set())
    assert result.spans == []
    # No markers in input -> output text equals input.
    assert result.text == text


@given(prefix=text_chunks, ec_suffix=st.text(alphabet="0123456789abcdef", min_size=6, max_size=12))
@settings(max_examples=50, deadline=None)
def test_known_marker_is_consumed(prefix: str, ec_suffix: str) -> None:
    ec_id = f"ec_{ec_suffix}"
    text = f"{prefix} 1.5% [{ec_id}]"
    result = parse_citations(text, {ec_id})
    assert "[ec_" not in result.text
    assert any(s.engine_call_id == ec_id for s in result.spans)


def test_full_citation_zero_uncited() -> None:
    text = "Return -2.1% [ec_aaaaaa] vs OMX -0.4% [ec_bbbbbb]."
    result = parse_citations(text, {"ec_aaaaaa", "ec_bbbbbb"})
    assert find_uncited_numerics(result.text, result.spans) == []
