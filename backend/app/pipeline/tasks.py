"""Celery tasks: crawl, ingest, attribution, briefings.

Each task is a thin sync wrapper that bootstraps an asyncio runtime and
delegates to a coroutine. Tasks are idempotent. Failures retry with
exponential backoff up to 3 times before alerting.
"""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select

from app.auth.models import Company, OrgCompanyAccess
from app.core.db import SessionLocal
from app.core.logging import logger
from app.crawlers import build as build_crawler
from app.crawlers.base import DateRange
from app.crawlers.company_ir_rss import CompanyIrRssCrawler
from app.engine.drivers.attribution import compute_attribution
from app.engine.drivers.briefing import generate_briefing
from app.ingestion.macro import ingest_macro
from app.ingestion.news import ingest_news
from app.ingestion.prices import ingest_prices
from app.pipeline.celery_app import celery_app

# ---------------------------------------------------------------------- crawls


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


@celery_app.task(name="crawl.yahoo", bind=True, max_retries=3, default_retry_delay=60)
def crawl_yahoo(self) -> int:
    return _run(_crawl_yahoo())


async def _crawl_yahoo() -> int:
    from app.crawlers.yahoo_finance import YahooFinanceCrawler

    async with SessionLocal() as session:
        symbols = (
            (
                await session.execute(
                    select(Company.yahoo_symbol).where(Company.active.is_(True))
                )
            )
            .scalars()
            .all()
        )
        if not symbols:
            return 0
        crawler = YahooFinanceCrawler(symbols=list(symbols))
        report = await crawler.crawl(session, DateRange.trailing(days=7))
        await session.commit()
        return report.rows_inserted


@celery_app.task(name="crawl.mfn", bind=True, max_retries=3, default_retry_delay=60)
def crawl_mfn(self) -> int:
    return _run(_crawl_mfn())


async def _crawl_mfn() -> int:
    from app.crawlers.mfn import MfnCrawler

    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(Company.mfn_slug, Company.ticker).where(
                    Company.active.is_(True), Company.mfn_slug.is_not(None)
                )
            )
        ).all()
        slug_map = {str(r[0]): str(r[1]) for r in rows if r[0]}
        if not slug_map:
            return 0
        crawler = MfnCrawler(slug_to_ticker=slug_map)
        report = await crawler.crawl(session, DateRange.trailing(days=2))
        await session.commit()
        return report.rows_inserted


@celery_app.task(
    name="crawl.riksbank", bind=True, max_retries=3, default_retry_delay=60
)
def crawl_riksbank(self) -> int:
    return _run(_simple_crawl("riksbank", days=7))


@celery_app.task(name="crawl.scb", bind=True, max_retries=3, default_retry_delay=60)
def crawl_scb(self) -> int:
    return _run(_simple_crawl("scb", days=60))


@celery_app.task(name="crawl.fred", bind=True, max_retries=3, default_retry_delay=60)
def crawl_fred(self) -> int:
    return _run(_simple_crawl("fred", days=14))


@celery_app.task(name="crawl.esap", bind=True, max_retries=3, default_retry_delay=60)
def crawl_esap(self) -> int:
    return _run(_simple_crawl("esap", days=2))


@celery_app.task(
    name="crawl.fi_insider", bind=True, max_retries=3, default_retry_delay=60
)
def crawl_fi_insider(self) -> int:
    return _run(_simple_crawl("fi_insider", days=2))


@celery_app.task(
    name="crawl.fi_short", bind=True, max_retries=3, default_retry_delay=60
)
def crawl_fi_short(self) -> int:
    return _run(_simple_crawl("fi_short", days=1))


@celery_app.task(name="crawl.ir_rss", bind=True, max_retries=3, default_retry_delay=60)
def crawl_ir_rss(self) -> int:
    return _run(_crawl_ir_rss())


async def _simple_crawl(name: str, *, days: int) -> int:
    async with SessionLocal() as session:
        crawler = build_crawler(name)
        report = await crawler.crawl(session, DateRange.trailing(days=days))
        await session.commit()
        return report.rows_inserted


async def _crawl_ir_rss() -> int:
    async with SessionLocal() as session:
        c = CompanyIrRssCrawler()
        c._feeds = await c.discover_feeds(session)
        if not c._feeds:
            return 0
        report = await c.crawl(session, DateRange.trailing(days=2))
        await session.commit()
        return report.rows_inserted


# ---------------------------------------------------------------------- ingest


@celery_app.task(name="ingest.all", bind=True, max_retries=3, default_retry_delay=60)
def ingest_all(self) -> dict[str, int]:
    return _run(_ingest_all())


async def _ingest_all() -> dict[str, int]:
    async with SessionLocal() as session:
        prices = await ingest_prices(session)
        news = await ingest_news(session)
        macro = await ingest_macro(session)
        await session.commit()
        return {"prices": prices, "news": news, "macro": macro}


# ---------------------------------------------------------------------- briefing


@celery_app.task(
    name="briefing.generate_for_company",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def briefing_generate_for_company(
    self, company_id: int, as_of_iso: str | None = None
) -> dict[str, Any]:
    return _run(_briefing_generate_for_company(company_id, as_of_iso))


async def _briefing_generate_for_company(
    company_id: int, as_of_iso: str | None
) -> dict[str, Any]:
    as_of = (
        date.fromisoformat(as_of_iso) if as_of_iso else date.today() - timedelta(days=1)
    )
    async with SessionLocal() as session:
        await compute_attribution(session, company_id=company_id, as_of=as_of)
        row = await generate_briefing(session, company_id=company_id, as_of=as_of)
        await session.commit()
        return {
            "briefing_id": row.id,
            "company_id": company_id,
            "as_of": as_of.isoformat(),
        }


@celery_app.task(name="briefing.generate_for_all_tickers", bind=True)
def briefing_generate_for_all(self) -> int:
    return _run(_briefing_generate_for_all())


async def _briefing_generate_for_all() -> int:
    """For every company that any org has marked is_primary=true, generate a
    briefing for yesterday. v1 ships a single briefing per (company, date)
    that all orgs share -- per-org peer overrides arrive in Phase 4."""
    async with SessionLocal() as session:
        rows = (
            (
                await session.execute(
                    select(Company.id)
                    .join(OrgCompanyAccess, OrgCompanyAccess.company_id == Company.id)
                    .where(OrgCompanyAccess.is_primary.is_(True))
                    .where(Company.active.is_(True))
                    .distinct()
                )
            )
            .scalars()
            .all()
        )
    n = 0
    for cid in rows:
        try:
            briefing_generate_for_company.delay(int(cid))
            n += 1
        except Exception as e:
            logger.exception("briefing_dispatch_failed", company_id=cid, error=str(e))
    return n
