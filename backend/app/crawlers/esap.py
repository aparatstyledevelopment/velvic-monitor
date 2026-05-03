"""ESAP (EU Single Access Point) regulatory filing crawler.

ESAP launched 2026; the access endpoints are stabilizing. The implementation
here mirrors the BaseCrawler pattern with a minimal XML payload shape and
serves as a robust skeleton -- the exact endpoint and filter shape MUST
be confirmed against ESAP's developer portal at production-deploy time.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from xml.etree import ElementTree as ET

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawlers.base import BaseCrawler, DateRange, PolitenessConfig
from app.crawlers.models import EsapFiling
from app.crawlers.registry import register


@dataclass(frozen=True)
class ParsedEsap:
    esap_id: str
    ticker: str | None
    filing_type: str | None
    title: str | None
    body_text: str | None
    filed_at: datetime
    source_url: str | None
    raw: dict[str, Any]


class EsapCrawler(BaseCrawler[ParsedEsap]):
    name = "esap"
    politeness = PolitenessConfig(min_interval_s=1.0)
    base_url = "https://esap.europa.eu/api/filings"

    def __init__(
        self,
        *,
        country: str = "SE",
        http_client: Any = None,
    ) -> None:
        super().__init__(http_client=http_client)
        self._country = country

    async def fetch_batches(self, window: DateRange) -> AsyncIterator[dict[str, Any]]:
        async with self.http() as client:
            resp = await self.get_with_retry(
                client,
                self.base_url,
                params={
                    "country": self._country,
                    "from": window.start.isoformat(),
                    "to": window.end.isoformat(),
                },
            )
            yield {"xml": resp.text}

    def parse(self, batch: dict[str, Any]) -> Sequence[ParsedEsap]:
        xml = batch.get("xml") or ""
        if not xml.strip():
            return []
        root = ET.fromstring(xml)
        out: list[ParsedEsap] = []
        for filing in root.findall("filing"):
            esap_id = (filing.findtext("id") or "").strip()
            if not esap_id:
                continue
            ticker = (filing.findtext("ticker") or "").strip() or None
            filing_type = (filing.findtext("type") or "").strip() or None
            title = (filing.findtext("title") or "").strip() or None
            body = (filing.findtext("body") or "").strip() or None
            filed = (filing.findtext("filedAt") or "").strip()
            try:
                filed_at = datetime.fromisoformat(filed.replace("Z", "+00:00"))
            except ValueError:
                continue
            url = (filing.findtext("url") or "").strip() or None
            out.append(
                ParsedEsap(
                    esap_id=esap_id,
                    ticker=ticker,
                    filing_type=filing_type,
                    title=title,
                    body_text=body,
                    filed_at=filed_at,
                    source_url=url,
                    raw={"esap_id": esap_id, "url": url},
                )
            )
        return out

    async def upsert_raw(
        self, session: AsyncSession, rows: Sequence[ParsedEsap]
    ) -> int:
        n = 0
        for r in rows:
            existing = await session.scalar(
                select(EsapFiling).where(EsapFiling.esap_id == r.esap_id)
            )
            if existing is not None:
                continue
            session.add(
                EsapFiling(
                    esap_id=r.esap_id,
                    ticker=r.ticker,
                    filing_type=r.filing_type,
                    title=r.title,
                    body_text=r.body_text,
                    filed_at=r.filed_at,
                    source_url=r.source_url,
                    raw_payload=r.raw,
                )
            )
            n += 1
        await session.flush()
        return n


@register("esap")
def _factory() -> EsapCrawler:
    return EsapCrawler()
