"""News ingestion: MFN + ESAP + IR-RSS -> curated news_item.

Authority-ranked dedup. When the same release appears in multiple sources,
we keep the highest-authority canonical row and stamp the others into
`also_seen_in`. Authority order: mfn > esap > ir_rss.

Dedup key (within a 24h window): canonical_title hash + company_id.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import Company
from app.crawlers.models import (
    CompanyIrRssItem,
    EsapFiling,
    MfnPressRelease,
)
from app.ingestion.models import NewsItem

_AUTHORITY = ("mfn", "esap", "ir_rss")
_AUTHORITY_RANK = {s: i for i, s in enumerate(_AUTHORITY)}


async def ingest_news(session: AsyncSession, *, since: datetime | None = None) -> int:
    """Promote new MFN/ESAP/IR-RSS rows into curated news_item with dedup."""
    since = since or (datetime.utcnow() - timedelta(days=7))
    candidates = list(await _gather_candidates(session, since=since))
    grouped: dict[tuple[int | None, str, str], list[_Candidate]] = {}
    for c in candidates:
        key = (c.company_id, c.dedup_window, c.dedup_hash)
        grouped.setdefault(key, []).append(c)

    upserted = 0
    for cands in grouped.values():
        cands.sort(key=lambda x: _AUTHORITY_RANK.get(x.source, 99))
        canonical = cands[0]
        also = [c.source for c in cands[1:]]
        existing = await session.scalar(
            select(NewsItem).where(
                NewsItem.source == canonical.source,
                NewsItem.source_row_id == canonical.source_row_id,
            )
        )
        if existing is not None:
            new_also = sorted({*existing.also_seen_in, *also})
            if new_also != list(existing.also_seen_in):
                existing.also_seen_in = new_also
                upserted += 1
            continue
        session.add(
            NewsItem(
                company_id=canonical.company_id,
                headline=canonical.headline,
                body_text=canonical.body_text,
                published_at=canonical.published_at,
                source=canonical.source,
                source_row_id=canonical.source_row_id,
                source_url=canonical.source_url,
                mar_flagged=canonical.mar_flagged,
                language=canonical.language,
                also_seen_in=also,
            )
        )
        upserted += 1
    await session.flush()
    return upserted


# ---------------------------------------------------------------------- helpers


@dataclass(frozen=True)
class _Candidate:
    company_id: int | None
    headline: str
    body_text: str | None
    published_at: datetime
    source: str
    source_row_id: int
    source_url: str
    mar_flagged: bool | None
    language: str | None
    dedup_hash: str
    dedup_window: str


async def _gather_candidates(
    session: AsyncSession, *, since: datetime
) -> Iterable[_Candidate]:
    yield_list: list[_Candidate] = []

    mfn_rows = (
        (
            await session.execute(
                select(MfnPressRelease).where(MfnPressRelease.fetched_at >= since)
            )
        )
        .scalars()
        .all()
    )
    for mfn in mfn_rows:
        company = await session.scalar(
            select(Company).where(Company.mfn_slug == mfn.ticker)
        ) or await _company_for_ticker(session, mfn.ticker)
        yield_list.append(
            _Candidate(
                company_id=company.id if company else None,
                headline=mfn.title,
                body_text=mfn.body_text,
                published_at=mfn.published_at,
                source="mfn",
                source_row_id=mfn.id,
                source_url=mfn.mfn_url,
                mar_flagged=mfn.mar_flagged,
                language=mfn.language,
                dedup_hash=_hash(mfn.title),
                dedup_window=_window_key(mfn.published_at),
            )
        )

    esap_rows = (
        (
            await session.execute(
                select(EsapFiling).where(EsapFiling.fetched_at >= since)
            )
        )
        .scalars()
        .all()
    )
    for esap in esap_rows:
        company = (
            await _company_for_ticker(session, esap.ticker) if esap.ticker else None
        )
        yield_list.append(
            _Candidate(
                company_id=company.id if company else None,
                headline=esap.title or (esap.filing_type or "regulatory filing"),
                body_text=esap.body_text,
                published_at=esap.filed_at,
                source="esap",
                source_row_id=esap.id,
                source_url=esap.source_url or "",
                mar_flagged=None,
                language=None,
                dedup_hash=_hash(esap.title or esap.filing_type or ""),
                dedup_window=_window_key(esap.filed_at),
            )
        )

    rss_rows = (
        (
            await session.execute(
                select(CompanyIrRssItem).where(CompanyIrRssItem.fetched_at >= since)
            )
        )
        .scalars()
        .all()
    )
    for rss in rss_rows:
        yield_list.append(
            _Candidate(
                company_id=rss.company_id,
                headline=rss.title,
                body_text=rss.body_text,
                published_at=rss.published_at,
                source="ir_rss",
                source_row_id=rss.id,
                source_url=rss.source_url,
                mar_flagged=None,
                language=None,
                dedup_hash=_hash(rss.title),
                dedup_window=_window_key(rss.published_at),
            )
        )

    return yield_list


async def _company_for_ticker(
    session: AsyncSession, ticker: str | None
) -> Company | None:
    if not ticker:
        return None
    result: Company | None = await session.scalar(
        select(Company).where(Company.ticker == ticker)
    )
    return result


def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
    return s


def _hash(s: str) -> str:
    return hashlib.sha256(_normalize(s).encode("utf-8")).hexdigest()[:16]


def _window_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")
