"""SCB PXWeb crawler. Phase-1 scope: CPI series only.

PXWeb is a POST-style API where the body picks dimensions. We keep the call
shape simple: one table per crawler invocation, latest N observations.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawlers.base import BaseCrawler, DateRange, PolitenessConfig
from app.crawlers.models import ScbObservation
from app.crawlers.registry import register


@dataclass(frozen=True)
class ParsedScb:
    table_id: str
    dimensions: dict[str, str]
    observation_date: date
    value: Decimal | None
    unit: str | None
    raw: dict[str, Any]


# CPI all-items, monthly. KPItotM is the historical 1980=100 base; SCB
# stopped updating it after 2025M12 and the active series from 2026 is the
# 2020=100 rebase. Operators must verify the live PXWeb tree and swap to
# the rebased table id (typically `KPI2020COICOPAR` for annual or the
# 2020=100 monthly successor) before turning on the SCB beat task in
# production. See docs/DATA_SOURCES.md.
DEFAULT_TABLE = "KPItotM"


class ScbCrawler(BaseCrawler[ParsedScb]):
    name = "scb"
    politeness = PolitenessConfig(min_interval_s=1.0)
    url = "https://api.scb.se/OV0104/v1/doris/en/ssd/PR/PR0101/PR0101A/{table}"

    def __init__(
        self,
        *,
        table_id: str = DEFAULT_TABLE,
        http_client: Any = None,
    ) -> None:
        super().__init__(http_client=http_client)
        self._table = table_id

    async def fetch_batches(self, window: DateRange) -> AsyncIterator[dict[str, Any]]:
        body = {
            "query": [],
            "response": {"format": "json"},
        }
        async with self.http() as client:
            resp = await self._post_with_retry(
                client, self.url.format(table=self._table), body
            )
            yield {"table_id": self._table, "data": resp.json()}

    async def _post_with_retry(
        self, client: httpx.AsyncClient, url: str, body: dict[str, Any]
    ) -> httpx.Response:
        # SCB PXWeb prefers POST -- mirror BaseCrawler.get_with_retry semantics.
        for attempt in range(self.politeness.max_retries):
            try:
                resp = await client.post(url, json=body)
                if resp.status_code in (429, 503):
                    raise httpx.HTTPError("transient")
                resp.raise_for_status()
                return resp
            except httpx.HTTPError:
                if attempt == self.politeness.max_retries - 1:
                    raise
        raise RuntimeError("unreachable")

    def parse(self, batch: dict[str, Any]) -> Sequence[ParsedScb]:
        table_id = batch["table_id"]
        data = batch["data"] or {}
        out: list[ParsedScb] = []
        for entry in data.get("data") or []:
            keys: list[str] = entry.get("key") or []
            values: list[str] = entry.get("values") or []
            if not keys or not values:
                continue
            month_str = keys[-1]
            try:
                obs_date = _parse_yyyymm(month_str)
            except ValueError:
                continue
            try:
                value = Decimal(values[0])
            except Exception:
                value = None
            dims = {f"d{i}": k for i, k in enumerate(keys[:-1])}
            out.append(
                ParsedScb(
                    table_id=table_id,
                    dimensions=dims,
                    observation_date=obs_date,
                    value=value,
                    unit=None,
                    raw=entry,
                )
            )
        return out

    async def upsert_raw(self, session: AsyncSession, rows: Sequence[ParsedScb]) -> int:
        n = 0
        for r in rows:
            existing = await session.scalar(
                select(ScbObservation).where(
                    ScbObservation.table_id == r.table_id,
                    ScbObservation.observation_date == r.observation_date,
                    ScbObservation.dimensions == r.dimensions,
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
                ScbObservation(
                    table_id=r.table_id,
                    dimensions=r.dimensions,
                    observation_date=r.observation_date,
                    value=r.value,
                    unit=r.unit,
                    raw_payload=r.raw,
                )
            )
            n += 1
        await session.flush()
        return n


def _parse_yyyymm(s: str) -> date:
    s = s.replace("M", "-")
    yyyy, mm = s.split("-")
    return date(int(yyyy), int(mm), 1)


@register("scb")
def _factory() -> ScbCrawler:
    return ScbCrawler()
