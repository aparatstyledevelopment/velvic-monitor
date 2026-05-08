"""Riksbank SWEA observation crawler.

Pulls scalar daily observations for the series we care about: policy rate,
SEK/EUR, SEK/USD, 10Y govt yield. Series IDs verified against the SWEA
catalog at production-deploy time; placeholders may need adjustment.

Authentication: SWEA migrated to Azure API Management; an
`Ocp-Apim-Subscription-Key` header is now required even for the rate /
exchange-rate read endpoints. Set `RIKSBANK_SUBSCRIPTION_KEY` to enable.
Without the key, requests succeed with status 200 but return a non-JSON
body that fails to parse (`Expecting value: line 1 column 1`).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.crawlers.base import BaseCrawler, CrawlerError, DateRange, PolitenessConfig
from app.crawlers.models import RiksbankObservation
from app.crawlers.registry import register

DEFAULT_SERIES = (
    "SECBREPOEFF",  # policy rate
    "SEKEURPMI",  # SEK/EUR mid
    "SEKUSDPMI",  # SEK/USD mid
    "SEKGVB10YC",  # 10Y govt yield
)


@dataclass(frozen=True)
class ParsedObs:
    series_id: str
    observation_date: date
    value: Decimal | None
    raw: dict[str, Any]


class RiksbankCrawler(BaseCrawler[ParsedObs]):
    name = "riksbank"
    politeness = PolitenessConfig(min_interval_s=0.4)
    base_url = "https://api.riksbank.se/swea/v1/Observations/{series}/{from_d}/{to_d}"

    def __init__(
        self,
        *,
        series_ids: Sequence[str] = DEFAULT_SERIES,
        http_client: Any = None,
    ) -> None:
        super().__init__(http_client=http_client)
        self._series = list(series_ids)

    async def fetch_batches(self, window: DateRange) -> AsyncIterator[dict[str, Any]]:
        key = get_settings().riksbank_subscription_key
        if not key:
            raise CrawlerError(
                "RIKSBANK_SUBSCRIPTION_KEY not set; SWEA requires an Azure APIM "
                "subscription key. Register at developer.api.riksbank.se, set "
                "the secret, and remove 'riksbank' from DISABLED_CRAWLERS."
            )
        headers = {"Ocp-Apim-Subscription-Key": key}
        async with self.http() as client:
            for sid in self._series:
                url = self.base_url.format(
                    series=sid,
                    from_d=window.start.isoformat(),
                    to_d=window.end.isoformat(),
                )
                resp = await self.get_with_retry(client, url, headers=headers)
                yield {"series_id": sid, "data": resp.json()}

    def parse(self, batch: dict[str, Any]) -> Sequence[ParsedObs]:
        sid = batch["series_id"]
        data = batch["data"]
        out: list[ParsedObs] = []
        for obs in data or []:
            d_raw = obs.get("date") or obs.get("Date")
            v_raw = obs.get("value") or obs.get("Value")
            if d_raw is None:
                continue
            try:
                d = date.fromisoformat(str(d_raw)[:10])
            except ValueError:
                continue
            v = None if v_raw is None else Decimal(str(v_raw))
            out.append(
                ParsedObs(
                    series_id=sid,
                    observation_date=d,
                    value=v,
                    raw=obs if isinstance(obs, dict) else {"value": v_raw},
                )
            )
        return out

    async def upsert_raw(self, session: AsyncSession, rows: Sequence[ParsedObs]) -> int:
        n = 0
        for r in rows:
            existing = await session.scalar(
                select(RiksbankObservation).where(
                    RiksbankObservation.series_id == r.series_id,
                    RiksbankObservation.observation_date == r.observation_date,
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
                RiksbankObservation(
                    series_id=r.series_id,
                    observation_date=r.observation_date,
                    value=r.value,
                    raw_payload=r.raw,
                )
            )
            n += 1
        await session.flush()
        return n


@register("riksbank")
def _factory() -> RiksbankCrawler:
    return RiksbankCrawler()
