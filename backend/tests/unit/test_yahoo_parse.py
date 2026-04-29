from datetime import UTC, datetime
from decimal import Decimal

from app.crawlers.yahoo_finance import YahooFinanceCrawler


def test_parse_extracts_bars() -> None:
    ts1 = int(datetime(2026, 4, 28, 0, 0, tzinfo=UTC).timestamp())
    ts2 = int(datetime(2026, 4, 29, 0, 0, tzinfo=UTC).timestamp())
    payload = {
        "chart": {
            "result": [
                {
                    "meta": {"symbol": "VOLV-B.ST"},
                    "timestamp": [ts1, ts2],
                    "indicators": {
                        "quote": [
                            {
                                "open": [251.5, 252.0],
                                "high": [253.0, 254.5],
                                "low": [250.0, 251.0],
                                "close": [252.5, 247.2],
                                "volume": [1_500_000, 1_700_000],
                            }
                        ],
                        "adjclose": [{"adjclose": [252.5, 247.2]}],
                    },
                }
            ]
        }
    }
    bars = list(YahooFinanceCrawler().parse(payload))
    assert len(bars) == 2
    assert bars[0].ticker == "VOLV-B.ST"
    assert bars[0].open == Decimal("251.5")
    assert bars[1].close == Decimal("247.2")
    assert bars[1].volume == 1_700_000


def test_parse_handles_empty_payload() -> None:
    assert list(YahooFinanceCrawler().parse({"chart": {"result": []}})) == []
    assert list(YahooFinanceCrawler().parse({})) == []
