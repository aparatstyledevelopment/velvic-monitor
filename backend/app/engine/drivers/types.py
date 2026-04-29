"""Pydantic return models for the Drivers Engine tools."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PriceBarOut(BaseModel):
    trading_date: date
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal
    volume: int | None


class PriceMove(BaseModel):
    ticker: str
    company_id: int
    last_close_date: date
    last_close: Decimal
    prior_close_date: date | None
    prior_close: Decimal | None
    daily_return_pct: Decimal | None
    five_day_history: list[PriceBarOut] = Field(default_factory=list)


class BenchmarkMove(BaseModel):
    benchmark: str
    as_of: date
    last_close: Decimal
    prior_close: Decimal | None
    daily_return_pct: Decimal | None


class PeerReturn(BaseModel):
    company_id: int
    ticker: str
    name: str
    daily_return_pct: Decimal | None


class PeerReturns(BaseModel):
    company_id: int
    as_of: date
    peers: list[PeerReturn]


class SectorReturn(BaseModel):
    company_id: int
    sector: str | None
    as_of: date
    daily_return_pct: Decimal | None
    proxy: str  # 'sector_index' | 'peer_average' | 'unavailable'


class MacroSeriesValue(BaseModel):
    series_code: str
    observation_date: date
    value: Decimal
    unit: str
    source: str


class MacroSnapshot(BaseModel):
    as_of: date
    series: list[MacroSeriesValue]


class NewsSummary(BaseModel):
    news_item_id: int
    headline: str
    summary: str | None
    published_at: datetime
    source: str
    source_url: str
    mar_flagged: bool | None


class NewsList(BaseModel):
    company_id: int
    start: date
    end: date
    items: list[NewsSummary]


class CompanyMeta(BaseModel):
    company_id: int
    ticker: str
    isin: str | None
    name: str
    market: str
    sector: str | None
    industry: str | None
    market_cap_band: str | None


class DailyAttributionOut(BaseModel):
    company_id: int
    as_of_date: date
    return_pct: Decimal | None
    benchmark_return_pct: Decimal | None
    sector_return_pct: Decimal | None
    relative_to_benchmark_pct: Decimal | None
    relative_to_sector_pct: Decimal | None


class QueryRow(BaseModel):
    columns: list[str]
    rows: list[list[str | int | float | bool | None]]
    truncated: bool = False


class QueryResult(BaseModel):
    sql: str
    result: QueryRow
