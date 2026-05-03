"""Yahoo Finance daily OHLCV crawler.

Uses the v8 chart endpoint (no API key, free tier ToS for non-commercial pilots).
Production deployments should swap for a paid feed -- see DATA_SOURCES.md.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
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
    base_url = "https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"

    def __init__(
        self,
        *,
        symbols: list[str] | None = None,
        http_client: Any = None,
    ) -> None:
        super().__init__(http_client=http_client)
        self._symbols = symbols or []

    async def fetch_batches(self, window: DateRange) -> AsyncIterator[dict[str, Any]]:
        period1 = int(
            datetime.combine(window.start, datetime.min.time(), UTC).timestamp()
        )
        period2 = int(
            datetime.combine(window.end, datetime.max.time(), UTC).timestamp()
        )
        async with self.http() as client:
            for symbol in self._symbols:
                resp = await self.get_with_retry(
                    client,
                    self.base_url.format(symbol=symbol),
                    params={
                        "period1": period1,
                        "period2": period2,
                        "interval": "1d",
                        "includeAdjustedClose": "true",
                    },
                )
                yield resp.json()

    def parse(self, batch: dict[str, Any]) -> Sequence[ParsedBar]:
        chart = batch.get("chart", {})
        result_list = chart.get("result") or []
        if not result_list:
            return []
        result = result_list[0]
        meta = result.get("meta", {})
        symbol = meta.get("symbol")
        timestamps = result.get("timestamp") or []
        indicators = result.get("indicators", {})
        quote = (indicators.get("quote") or [{}])[0]
        adj = (indicators.get("adjclose") or [{}])[0]

        opens = quote.get("open") or [None] * len(timestamps)
        highs = quote.get("high") or [None] * len(timestamps)
        lows = quote.get("low") or [None] * len(timestamps)
        closes = quote.get("close") or [None] * len(timestamps)
        volumes = quote.get("volume") or [None] * len(timestamps)
        adjs = adj.get("adjclose") or [None] * len(timestamps)

        out: list[ParsedBar] = []
        for i, ts in enumerate(timestamps):
            d = datetime.fromtimestamp(ts, tz=UTC).date()
            out.append(
                ParsedBar(
                    ticker=symbol,
                    trading_date=d,
                    open=_dec(opens[i]),
                    high=_dec(highs[i]),
                    low=_dec(lows[i]),
                    close=_dec(closes[i]),
                    adj_close=_dec(adjs[i]),
                    volume=int(volumes[i]) if volumes[i] is not None else None,
                    raw={
                        "ts": ts,
                        "o": opens[i],
                        "h": highs[i],
                        "l": lows[i],
                        "c": closes[i],
                        "ac": adjs[i],
                        "v": volumes[i],
                    },
                )
            )
        return out

    async def upsert_raw(self, session: AsyncSession, rows: Sequence[ParsedBar]) -> int:
        if not rows:
            return 0
        n = 0
        for r in rows:
            existing = await session.scalar(
                select(YahooPriceBar).where(
                    YahooPriceBar.ticker == r.ticker,
                    YahooPriceBar.trading_date == r.trading_date,
                    YahooPriceBar.superseded_by.is_(None),
                )
            )
            if existing is not None:
                if _bar_equal(existing, r):
                    continue
                # Supersede the prior fetch when content differs.
                new_row = YahooPriceBar(
                    ticker=r.ticker,
                    trading_date=r.trading_date,
                    open=r.open,
                    high=r.high,
                    low=r.low,
                    close=r.close,
                    adj_close=r.adj_close,
                    volume=r.volume,
                    raw_payload=r.raw,
                )
                session.add(new_row)
                await session.flush()
                existing.superseded_by = new_row.id
                await session.flush()
                n += 1
                continue
            session.add(
                YahooPriceBar(
                    ticker=r.ticker,
                    trading_date=r.trading_date,
                    open=r.open,
                    high=r.high,
                    low=r.low,
                    close=r.close,
                    adj_close=r.adj_close,
                    volume=r.volume,
                    raw_payload=r.raw,
                )
            )
            n += 1
        await session.flush()
        return n


def _dec(v: Any) -> Decimal | None:
    if v is None:
        return None
    return Decimal(str(v))


def _bar_equal(existing: YahooPriceBar, new: ParsedBar) -> bool:
    return (
        existing.open == new.open
        and existing.high == new.high
        and existing.low == new.low
        and existing.close == new.close
        and existing.adj_close == new.adj_close
        and existing.volume == new.volume
    )


@register("yahoo_finance")
def _factory() -> YahooFinanceCrawler:
    return YahooFinanceCrawler()


# Keep insert imported (used in companion utilities/tests later)
_ = insert
