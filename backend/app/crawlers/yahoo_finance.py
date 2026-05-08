"""Yahoo Finance daily OHLCV crawler.

Yahoo's `/v8/finance/chart/` endpoint returns 403 to plain HTTP clients (TLS
fingerprint detection); yfinance bypasses it via curl_cffi Chrome
impersonation. We delegate the network call to yfinance and keep the rest of
the crawler -- parse, upsert, dedup -- pure so unit tests can drive it with
list-of-record fixtures without touching the network.

Tier-1 isolation (ADR 0002, ADR 0005) means switching to a paid feed
(Millistream / Refinitiv / Polygon) is a Tier-1 + ingestion change with no
Engine impact -- planned pre-LOI.
"""

from __future__ import annotations

import asyncio
import math
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, cast

import yfinance as yf
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawlers.base import BaseCrawler, DateRange, PolitenessConfig
from app.crawlers.models import YahooPriceBar
from app.crawlers.registry import register


@dataclass(frozen=True)
class ParsedBar:
    ticker: str
    trading_date: date
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal | None
    adj_close: Decimal | None
    volume: int | None
    raw: dict[str, Any]


class YahooFinanceCrawler(BaseCrawler[ParsedBar]):
    name = "yahoo_finance"
    politeness = PolitenessConfig(min_interval_s=0.6)

    def __init__(
        self,
        *,
        symbols: list[str] | None = None,
        http_client: Any = None,
    ) -> None:
        super().__init__(http_client=http_client)
        self._symbols = symbols or []

    async def fetch_batches(self, window: DateRange) -> AsyncIterator[dict[str, Any]]:
        for symbol in self._symbols:
            records = await asyncio.to_thread(
                _yf_history_records, symbol, window.start, window.end
            )
            if self.politeness.min_interval_s > 0:
                await asyncio.sleep(self.politeness.min_interval_s)
            yield {"symbol": symbol, "records": records}

    def parse(self, batch: dict[str, Any]) -> Sequence[ParsedBar]:
        symbol = batch.get("symbol")
        records: list[dict[str, Any]] = batch.get("records") or []
        if not symbol or not records:
            return []
        out: list[ParsedBar] = []
        for rec in records:
            d = _to_date(rec.get("Date"))
            if d is None:
                continue
            out.append(
                ParsedBar(
                    ticker=symbol,
                    trading_date=d,
                    open=_dec(rec.get("Open")),
                    high=_dec(rec.get("High")),
                    low=_dec(rec.get("Low")),
                    close=_dec(rec.get("Close")),
                    adj_close=_dec(rec.get("Adj Close") or rec.get("Close")),
                    volume=_int(rec.get("Volume")),
                    raw={
                        "date": d.isoformat(),
                        "o": _jsonable(rec.get("Open")),
                        "h": _jsonable(rec.get("High")),
                        "l": _jsonable(rec.get("Low")),
                        "c": _jsonable(rec.get("Close")),
                        "ac": _jsonable(rec.get("Adj Close")),
                        "v": _jsonable(rec.get("Volume")),
                    },
                )
            )
        return out

    async def upsert_raw(self, session: AsyncSession, rows: Sequence[ParsedBar]) -> int:
        # Insert-or-skip via the partial unique index `yahoo_price_bar_unique
        # ON (ticker, trading_date) WHERE superseded_by IS NULL`. The previous
        # ORM-level "version on diff" path was unsound for two reasons:
        #   1. NUMERIC(20,6) rounds inputs on storage, so an exact Decimal
        #      compare on the round-tripped value (_bar_equal) returned False
        #      for unchanged rows -- spuriously triggering versioning.
        #   2. The versioning path inserted the new row with superseded_by
        #      still NULL before marking the old row superseded, which caused
        #      both rows to occupy the partial index simultaneously and trip
        #      the unique constraint.
        # Phase 1 doesn't need retro-correction tracking; ON CONFLICT DO
        # NOTHING is the correct idempotent primitive here. When/if Yahoo
        # back-corrections matter (Phase 2+), reintroduce versioning by
        # marking the existing row superseded BEFORE inserting the new one.
        if not rows:
            return 0
        values = [
            {
                "ticker": r.ticker,
                "trading_date": r.trading_date,
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "adj_close": r.adj_close,
                "volume": r.volume,
                "raw_payload": r.raw,
            }
            for r in rows
        ]
        stmt = (
            pg_insert(YahooPriceBar)
            .values(values)
            .on_conflict_do_nothing(
                index_elements=["ticker", "trading_date"],
                index_where=YahooPriceBar.superseded_by.is_(None),
            )
        )
        result = await session.execute(stmt)
        await session.flush()
        # Result.rowcount is concrete on the async cursor result but the
        # typeshed stub only exposes the abstract Result[Any]; cast to keep
        # mypy --strict happy without weakening the runtime contract.
        return cast(int, getattr(result, "rowcount", 0)) or 0


def _yf_history_records(symbol: str, start: date, end: date) -> list[dict[str, Any]]:
    """Sync helper executed in a thread; isolates pandas + yfinance from async code."""
    df = yf.Ticker(symbol).history(
        start=start.isoformat(),
        end=(end.toordinal() - start.toordinal() and end.isoformat())
        or end.isoformat(),
        interval="1d",
        auto_adjust=False,
    )
    if df is None or df.empty:
        return []
    records: list[dict[str, Any]] = df.reset_index().to_dict(orient="records")
    return records


def _dec(v: Any) -> Decimal | None:
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    try:
        return Decimal(str(v))
    except Exception:
        return None


def _int(v: Any) -> int | None:
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    try:
        return int(v)
    except Exception:
        return None


def _to_date(v: Any) -> date | None:
    if v is None:
        return None
    # Order matters: datetime/Timestamp must be checked before date because
    # `pandas.Timestamp` inherits from `datetime.datetime` which inherits from
    # `datetime.date`. `isinstance(ts, date)` is True for a Timestamp, so the
    # naive order (date first) returns the Timestamp unchanged and downstream
    # SQLAlchemy comparisons mis-match the stored DATE column, causing the
    # idempotent-upsert path to fall through to a duplicate INSERT.
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if hasattr(v, "to_pydatetime"):
        # pandas Timestamp; to_pydatetime() returns datetime.
        dt: datetime = v.to_pydatetime()
        return dt.date()
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v[:10]).date()
        except ValueError:
            return None
    if isinstance(v, int | float):
        try:
            return datetime.fromtimestamp(float(v), tz=UTC).date()
        except (OverflowError, OSError, ValueError):
            return None
    return None


def _jsonable(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if isinstance(v, str | int | bool):
        return v
    if isinstance(v, float):
        return v
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


@register("yahoo_finance")
def _factory() -> YahooFinanceCrawler:
    return YahooFinanceCrawler()
