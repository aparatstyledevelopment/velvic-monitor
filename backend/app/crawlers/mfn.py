"""MFN regulatory press-release crawler.

MFN serves per-issuer Atom/RSS feeds that we ingest verbatim into Tier-1.
We extract MAR flag from feed-level metadata when present.
"""
from __future__ import annotations

import re
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from xml.etree import ElementTree as ET

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawlers.base import BaseCrawler, DateRange, PolitenessConfig
from app.crawlers.models import MfnPressRelease
from app.crawlers.registry import register


@dataclass(frozen=True)
class ParsedMfn:
    mfn_id: str
    ticker: str
    title: str
    body_html: str | None
    body_text: str | None
    published_at: datetime
    mfn_url: str
    mar_flagged: bool | None
    language: str | None
    raw: dict[str, Any]


_NS = {"atom": "http://www.w3.org/2005/Atom"}
_HTML_TAG = re.compile(r"<[^>]+>")


class MfnCrawler(BaseCrawler[ParsedMfn]):
    name = "mfn"
    politeness = PolitenessConfig(min_interval_s=1.0)

    def __init__(
        self,
        *,
        slug_to_ticker: dict[str, str] | None = None,
        http_client: Any = None,
    ) -> None:
        super().__init__(http_client=http_client)
        self._slugs = slug_to_ticker or {}

    async def fetch_batches(self, window: DateRange) -> AsyncIterator[dict[str, Any]]:
        async with self.http() as client:
            for slug, ticker in self._slugs.items():
                resp = await self.get_with_retry(
                    client, f"https://mfn.se/all/a/{slug}?format=atom"
                )
                yield {"ticker": ticker, "xml": resp.text}

    def parse(self, batch: dict[str, Any]) -> Sequence[ParsedMfn]:
        ticker = batch["ticker"]
        xml = batch["xml"]
        if not xml.strip():
            return []
        root = ET.fromstring(xml)
        out: list[ParsedMfn] = []
        for entry in root.findall("atom:entry", _NS):
            entry_id = _text(entry, "atom:id")
            if not entry_id:
                continue
            title = _text(entry, "atom:title") or ""
            link_el = entry.find("atom:link", _NS)
            link = link_el.attrib.get("href", "") if link_el is not None else ""
            updated = _text(entry, "atom:updated") or _text(entry, "atom:published")
            try:
                published_at = (
                    datetime.fromisoformat(updated.replace("Z", "+00:00")) if updated else datetime.utcnow()
                )
            except ValueError:
                continue
            content_el = entry.find("atom:content", _NS)
            body_html = content_el.text if content_el is not None else None
            body_text = _HTML_TAG.sub("", body_html or "").strip() or None
            mar_flagged = _detect_mar(title, body_text)
            language = _detect_lang(title)
            out.append(
                ParsedMfn(
                    mfn_id=entry_id,
                    ticker=ticker,
                    title=title,
                    body_html=body_html,
                    body_text=body_text,
                    published_at=published_at,
                    mfn_url=link,
                    mar_flagged=mar_flagged,
                    language=language,
                    raw={"atom_id": entry_id, "title": title, "link": link},
                )
            )
        return out

    async def upsert_raw(
        self, session: AsyncSession, rows: Sequence[ParsedMfn]
    ) -> int:
        n = 0
        for r in rows:
            existing = await session.scalar(
                select(MfnPressRelease).where(MfnPressRelease.mfn_id == r.mfn_id)
            )
            if existing is not None:
                continue
            session.add(
                MfnPressRelease(
                    mfn_id=r.mfn_id,
                    ticker=r.ticker,
                    title=r.title,
                    body_html=r.body_html,
                    body_text=r.body_text,
                    published_at=r.published_at,
                    mfn_url=r.mfn_url,
                    mar_flagged=r.mar_flagged,
                    language=r.language,
                    raw_payload=r.raw,
                )
            )
            n += 1
        await session.flush()
        return n


def _text(el: ET.Element, path: str) -> str | None:
    found = el.find(path, _NS)
    return found.text.strip() if found is not None and found.text else None


def _detect_mar(title: str, body: str | None) -> bool:
    haystack = f"{title} {body or ''}".lower()
    return any(
        marker in haystack
        for marker in ("mar", "insider", "insiderinformation", "marknadsmissbruk")
    )


def _detect_lang(title: str) -> str | None:
    if any(c in title for c in "åäöÅÄÖ"):
        return "sv"
    return "en"


@register("mfn")
def _factory() -> MfnCrawler:
    return MfnCrawler()
