"""Per-company IR RSS feed crawler.

Each onboarded company carries its own ir_rss_url. We poll all configured
feeds in a single crawler run; dedup by (company_id, guid).
"""
from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from xml.etree import ElementTree as ET

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import Company
from app.crawlers.base import BaseCrawler, DateRange, PolitenessConfig
from app.crawlers.models import CompanyIrRssItem
from app.crawlers.registry import register


@dataclass(frozen=True)
class ParsedRss:
    company_id: int
    guid: str
    title: str
    body_html: str | None
    body_text: str | None
    published_at: datetime
    source_url: str
    raw: dict[str, Any]


class CompanyIrRssCrawler(BaseCrawler[ParsedRss]):
    name = "company_ir_rss"
    politeness = PolitenessConfig(min_interval_s=1.5)

    def __init__(
        self,
        *,
        feeds: list[tuple[int, str]] | None = None,
        http_client: Any = None,
    ) -> None:
        super().__init__(http_client=http_client)
        self._feeds = feeds or []

    async def discover_feeds(self, session: AsyncSession) -> list[tuple[int, str]]:
        rows = (
            await session.execute(
                select(Company.id, Company.ir_rss_url).where(
                    Company.active.is_(True), Company.ir_rss_url.is_not(None)
                )
            )
        ).all()
        return [(int(r[0]), str(r[1])) for r in rows if r[1]]

    async def fetch_batches(self, window: DateRange) -> AsyncIterator[dict[str, Any]]:
        async with self.http() as client:
            for company_id, url in self._feeds:
                resp = await self.get_with_retry(client, url)
                yield {"company_id": company_id, "xml": resp.text, "url": url}

    def parse(self, batch: dict[str, Any]) -> Sequence[ParsedRss]:
        xml = batch.get("xml") or ""
        company_id = batch["company_id"]
        if not xml.strip():
            return []
        root = ET.fromstring(xml)
        # Support RSS 2.0 (channel/item) and Atom (entry)
        items = list(root.iter("item")) + list(
            root.iter("{http://www.w3.org/2005/Atom}entry")
        )
        out: list[ParsedRss] = []
        for it in items:
            guid = _first_text(it, ["guid", "{http://www.w3.org/2005/Atom}id"])
            title = _first_text(it, ["title", "{http://www.w3.org/2005/Atom}title"])
            link = _first_text(
                it, ["link"], attr_fallback="href"
            )
            pub = _first_text(
                it,
                ["pubDate", "{http://www.w3.org/2005/Atom}updated", "{http://www.w3.org/2005/Atom}published"],
            )
            desc = _first_text(
                it,
                ["description", "{http://www.w3.org/2005/Atom}summary", "{http://www.w3.org/2005/Atom}content"],
            )
            if not guid or not title or not pub:
                continue
            try:
                if pub.endswith("Z"):
                    published_at = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                else:
                    published_at = _parse_rfc822(pub)
            except (ValueError, TypeError):
                continue
            out.append(
                ParsedRss(
                    company_id=company_id,
                    guid=guid,
                    title=title,
                    body_html=desc,
                    body_text=desc,
                    published_at=published_at,
                    source_url=link or batch.get("url", ""),
                    raw={"guid": guid, "title": title},
                )
            )
        return out

    async def upsert_raw(
        self, session: AsyncSession, rows: Sequence[ParsedRss]
    ) -> int:
        n = 0
        for r in rows:
            existing = await session.scalar(
                select(CompanyIrRssItem).where(
                    CompanyIrRssItem.company_id == r.company_id,
                    CompanyIrRssItem.guid == r.guid,
                )
            )
            if existing is not None:
                continue
            session.add(
                CompanyIrRssItem(
                    company_id=r.company_id,
                    guid=r.guid,
                    title=r.title,
                    body_html=r.body_html,
                    body_text=r.body_text,
                    published_at=r.published_at,
                    source_url=r.source_url,
                    raw_payload=r.raw,
                )
            )
            n += 1
        await session.flush()
        return n


def _first_text(
    el: ET.Element, paths: list[str], *, attr_fallback: str | None = None
) -> str | None:
    for p in paths:
        node = el.find(p)
        if node is None:
            continue
        if node.text and node.text.strip():
            return node.text.strip()
        if attr_fallback and attr_fallback in node.attrib:
            return node.attrib[attr_fallback]
    return None


def _parse_rfc822(s: str) -> datetime:
    from email.utils import parsedate_to_datetime

    return parsedate_to_datetime(s)


@register("company_ir_rss")
def _factory() -> CompanyIrRssCrawler:
    return CompanyIrRssCrawler()
