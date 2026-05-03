"""FRED (St Louis Fed) macro-series crawler. Free API key required."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.crawlers.base import BaseCrawler, DateRange, PolitenessConfig
from app.crawlers.models import FredObservation
from app.crawlers.registry import register

DEFAULT_SERIES = (
    "DCOILBRENTEU",  # Brent crude
    "DGS10",  # 10Y US Treasury
    "DEXUSEU",  # USD/EUR
)


@dataclass(frozen=True)
class ParsedFred:
    series_id: str
    observation_date: date
    value: Decimal | None
    raw: dict[str, Any]


class FredCrawler(BaseCrawler[ParsedFred]):
    name = "fred"
    politeness = PolitenessConfig(min_interval_s=0.3)
    base_url = "https://api.stlouisfed.org/fred/series/observations"

    def __init__(
        self,
        *,
        series_ids: Sequence[str] = DEFAULT_SERIES,
        api_key: str | None = None,
        http_client: Any = None,
    ) -> None:
        super().__init__(http_client=http_client)
        self._series = list(series_ids)
        self._api_key = api_key

    async def fetch_batches(self, window: DateRange) -> AsyncIterator[dict[str, Any]]:
        api_key = self._api_key or get_settings().fred_api_key
        if not api_key:
            return
        async with self.http() as client:
            for sid in self._series:
                resp = await self.get_with_retry(
                    client,
                    self.base_url,
                    params={
                        "series_id": sid,
                        "api_key": api_key,
                        "file_type": "json",
                        "observation_start": window.start.isoformat(),
                        "observation_end": window.end.isoformat(),
                    },
                )
                yield {"series_id": sid, "data": resp.json()}

    def parse(self, batch: dict[str, Any]) -> Sequence[ParsedFred]:
        sid = batch["series_id"]
        data = batch["data"] or {}
        out: list[ParsedFred] = []
        for obs in data.get("observations") or []:
            d_raw = obs.get("date")
            v_raw = obs.get("value")
            if not d_raw:
                continue
            try:
                d = date.fromisoformat(d_raw)
            except ValueError:
                continue
            value: Decimal | None
            if v_raw in (None, "", "."):
                value = None
            else:
                try:
                    value = Decimal(v_raw)
                except Exception:
                    value = None
            out.append(
                ParsedFred(series_id=sid, observation_date=d, value=value, raw=obs)
            )
        return out

    async def upsert_raw(
        self, session: AsyncSession, rows: Sequence[ParsedFred]
    ) -> int:
        n = 0
        for r in rows:
            existing = await session.scalar(
                select(FredObservation).where(
                    FredObservation.series_id == r.series_id,
                    FredObservation.observation_date == r.observation_date,
                )
            )
            if existing is not None:
                if existing.value == r.value:
                    continue
                existing.value = r.value
                existing.raw_payload = r.raw
                n += 1
                continue
            session.add(
                FredObservation(
                    series_id=r.series_id,
                    observation_date=r.observation_date,
                    value=r.value,
                    raw_payload=r.raw,
                )
            )
            n += 1
        await session.flush()
        return n


@register("fred")
def _factory() -> FredCrawler:
    return FredCrawler()
