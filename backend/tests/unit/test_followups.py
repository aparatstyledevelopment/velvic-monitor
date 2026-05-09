"""Unit tests for chat.followups.

The followup generator is a small deterministic surface; we just need to
prove that (a) the keyword library steers selection, (b) tool-name fallback
kicks in when text is empty, (c) the cold-start tail fills any remaining
slots, and (d) the result always has length <= 3 with no duplicates.
"""

from __future__ import annotations

from app.chat import followups


def test_returns_three_unique_strings_for_typical_text() -> None:
    out = followups.generate(
        final_text="Volvo's price was down 1.2%, peers also down on the day.",
        tool_names=["get_price_move", "get_peer_returns"],
    )
    assert len(out) == 3
    assert len(set(out)) == 3


def test_text_keywords_drive_selection() -> None:
    out = followups.generate(
        final_text="The macro snapshot shows EUR/SEK weaker today.",
        tool_names=[],
    )
    assert "How did FX move against the SEK today?" in out


def test_tool_names_provide_fallback_when_text_is_empty() -> None:
    out = followups.generate(
        final_text="",
        tool_names=["get_news_for_company"],
    )
    assert "Summarise today's regulatory news" in out


def test_cold_start_tail_fills_when_nothing_matches() -> None:
    out = followups.generate(final_text="", tool_names=[])
    assert out == [
        "Did peers move similarly today?",
        "Any MAR-flagged news in the last 30 days?",
        "Compare against the closest peers",
    ]


def test_caps_at_three() -> None:
    text = "price benchmark sector peer news insider short ownership attribution macro"
    out = followups.generate(final_text=text, tool_names=[])
    assert len(out) == 3
