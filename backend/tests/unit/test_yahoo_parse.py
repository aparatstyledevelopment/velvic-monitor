from datetime import date
from decimal import Decimal

from app.crawlers.yahoo_finance import YahooFinanceCrawler


def test_parse_extracts_bars_from_yfinance_records() -> None:
    batch = {
        "symbol": "VOLV-B.ST",
        "records": [
            {
                "Date": date(2026, 4, 28),
                "Open": 251.5,
                "High": 253.0,
                "Low": 250.0,
                "Close": 252.5,
                "Adj Close": 252.5,
                "Volume": 1_500_000,
            },
            {
                "Date": date(2026, 4, 29),
                "Open": 252.0,
                "High": 254.5,
                "Low": 251.0,
                "Close": 247.2,
                "Adj Close": 247.2,
                "Volume": 1_700_000,
            },
        ],
    }
    bars = list(YahooFinanceCrawler().parse(batch))
    assert len(bars) == 2
    assert bars[0].ticker == "VOLV-B.ST"
    assert bars[0].open == Decimal("251.5")
    assert bars[1].close == Decimal("247.2")
    assert bars[1].volume == 1_700_000


def test_parse_handles_empty_records() -> None:
    assert list(YahooFinanceCrawler().parse({"symbol": "X.ST", "records": []})) == []
    assert list(YahooFinanceCrawler().parse({})) == []


def test_parse_skips_records_with_missing_date() -> None:
    batch = {
        "symbol": "X.ST",
        "records": [
            {"Open": 100, "Close": 101},
            {"Date": date(2026, 4, 28), "Open": 100, "Close": 101},
        ],
    }
    bars = list(YahooFinanceCrawler().parse(batch))
    assert len(bars) == 1
    assert bars[0].trading_date == date(2026, 4, 28)


def test_parse_drops_nan_floats() -> None:
    batch = {
        "symbol": "X.ST",
        "records": [
            {
                "Date": date(2026, 4, 28),
                "Open": float("nan"),
                "High": float("nan"),
                "Low": float("nan"),
                "Close": 100.0,
                "Volume": 12345,
            }
        ],
    }
    bars = list(YahooFinanceCrawler().parse(batch))
    assert len(bars) == 1
    assert bars[0].open is None
    assert bars[0].close == Decimal("100.0")
