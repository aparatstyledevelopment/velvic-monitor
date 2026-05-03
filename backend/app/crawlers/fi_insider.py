"""Finansinspektionen Insynsregistret (PDMR transactions) crawler.

FI publishes a CSV of insider transactions; we parse and persist verbatim.
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
from app.crawlers.models import FiInsiderTransaction
from app.crawlers.registry import register


@dataclass(frozen=True)
class ParsedInsider:
    publication_id: str
    issuer: str
    person: str
    role: str | None
    transaction_type: str
    shares: Decimal | None
    price: Decimal | None
    value: Decimal | None
    currency: str | None
    transaction_date: date
    raw: dict[str, Any]


class FiInsiderCrawler(BaseCrawler[ParsedInsider]):
    name = "fi_insider"
    politeness = PolitenessConfig(min_interval_s=2.0)
    base_url = "https://marknadssok.fi.se/publiceringsklient/en-GB/Search/Search"

    async def fetch_batches(self, window: DateRange) -> AsyncIterator[dict[str, Any]]:
        async with self.http() as client:
            resp = await self.get_with_retry(
                client,
                self.base_url,
                params={
                    "Utgivare": "",
                    "PersonILedandeStallningNamn": "",
                    "Transaktionsdatum.From": window.start.strftime("%Y-%m-%d"),
                    "Transaktionsdatum.To": window.end.strftime("%Y-%m-%d"),
                    "button": "export",
                    "Page": 1,
                },
                headers={"Accept": "text/csv"},
            )
            yield {"csv": resp.text}

    def parse(self, batch: dict[str, Any]) -> Sequence[ParsedInsider]:
        text = batch.get("csv") or ""
        if not text.strip():
            return []
        out: list[ParsedInsider] = []
        reader = csv.DictReader(io.StringIO(text), delimiter=";")
        for row in reader:
            pub_id = (
                (row.get("Publiceringsdatum") or "")
                + "|"
                + (row.get("Utgivare") or "")
                + "|"
                + (row.get("PersonILedandeStallningNamn") or "")
            )
            issuer = row.get("Utgivare") or ""
            person = row.get("PersonILedandeStallningNamn") or ""
            if not issuer or not person:
                continue
            try:
                tdate = date.fromisoformat(row.get("Transaktionsdatum", "")[:10])
            except ValueError:
                continue
            out.append(
                ParsedInsider(
                    publication_id=pub_id,
                    issuer=issuer,
                    person=person,
                    role=row.get("Befattning") or None,
                    transaction_type=row.get("Karaktar") or "unknown",
                    shares=_dec(row.get("Volym")),
                    price=_dec(row.get("Pris")),
                    value=_dec(row.get("Omsattning")),
                    currency=row.get("Valuta") or None,
                    transaction_date=tdate,
                    raw=dict(row),
                )
            )
        return out

    async def upsert_raw(
        self, session: AsyncSession, rows: Sequence[ParsedInsider]
    ) -> int:
        n = 0
        for r in rows:
            existing = await session.scalar(
                select(FiInsiderTransaction).where(
                    FiInsiderTransaction.publication_id == r.publication_id
                )
            )
            if existing is not None:
                continue
            session.add(
                FiInsiderTransaction(
                    publication_id=r.publication_id,
                    issuer=r.issuer,
                    person=r.person,
                    role=r.role,
                    transaction_type=r.transaction_type,
                    shares=r.shares,
                    price=r.price,
                    value=r.value,
                    currency=r.currency,
                    transaction_date=r.transaction_date,
                    raw_payload=r.raw,
                )
            )
            n += 1
        await session.flush()
        return n


def _dec(v: Any) -> Decimal | None:
    if v in (None, "", "-"):
        return None
    try:
        return Decimal(str(v).replace(",", ".").replace(" ", ""))
    except Exception:
        return None


@register("fi_insider")
def _factory() -> FiInsiderCrawler:
    return FiInsiderCrawler()
