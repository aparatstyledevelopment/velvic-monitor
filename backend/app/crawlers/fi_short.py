"""Finansinspektionen Blankningsregistret (net short positions) crawler.

FI publishes daily snapshots; we ingest the latest, dedup by
(issuer, position_holder, position_date).
"""
from __future__ import annotations

import csv
import io
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawlers.base import BaseCrawler, DateRange, PolitenessConfig
from app.crawlers.models import FiShortPosition
from app.crawlers.registry import register


@dataclass(frozen=True)
class ParsedShort:
    issuer: str
    position_holder: str
    position_pct: Decimal
    position_date: date
    raw: dict[str, Any]


class FiShortCrawler(BaseCrawler[ParsedShort]):
    name = "fi_short"
    politeness = PolitenessConfig(min_interval_s=2.0)
    base_url = "https://www.fi.se/sv/vara-register/blankningsregistret/GetAktuellFile/"

    async def fetch_batches(self, window: DateRange) -> AsyncIterator[dict[str, Any]]:
        async with self.http() as client:
            resp = await self.get_with_retry(client, self.base_url)
            yield {"csv": resp.text, "as_of": window.end}

    def parse(self, batch: dict[str, Any]) -> Sequence[ParsedShort]:
        text = batch.get("csv") or ""
        as_of: date = batch["as_of"]
        if not text.strip():
            return []
        out: list[ParsedShort] = []
        reader = csv.DictReader(io.StringIO(text), delimiter=";")
        for row in reader:
            issuer = (row.get("Utgivare") or row.get("Issuer") or "").strip()
            holder = (
                row.get("Innehavare av positionen") or row.get("PositionHolder") or ""
            ).strip()
            pct_raw = row.get("Position i procent") or row.get("Position") or ""
            if not issuer or not holder:
                continue
            try:
                pct = Decimal(str(pct_raw).replace(",", ".").replace("%", "").strip())
            except Exception:
                continue
            out.append(
                ParsedShort(
                    issuer=issuer,
                    position_holder=holder,
                    position_pct=pct,
                    position_date=as_of,
                    raw=dict(row),
                )
            )
        return out

    async def upsert_raw(
        self, session: AsyncSession, rows: Sequence[ParsedShort]
    ) -> int:
        n = 0
        for r in rows:
            existing = await session.scalar(
                select(FiShortPosition).where(
                    FiShortPosition.issuer == r.issuer,
                    FiShortPosition.position_holder == r.position_holder,
                    FiShortPosition.position_date == r.position_date,
                )
            )
            if existing is not None:
                if existing.position_pct == r.position_pct:
                    continue
                existing.position_pct = r.position_pct
                existing.raw_payload = r.raw
                n += 1
                continue
            session.add(
                FiShortPosition(
                    issuer=r.issuer,
                    position_holder=r.position_holder,
                    position_pct=r.position_pct,
                    position_date=r.position_date,
                    raw_payload=r.raw,
                )
            )
            n += 1
        await session.flush()
        return n


@register("fi_short")
def _factory() -> FiShortCrawler:
    return FiShortCrawler()
