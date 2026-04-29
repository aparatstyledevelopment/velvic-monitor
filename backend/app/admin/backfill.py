"""End-to-end backfill: crawl + ingest + attribution + briefings.

Runs every step in-process (no Celery dispatch) for the demo seed.
Intended for local development and the first deploy's smoke test.

Run: `python -m app.admin.backfill`
"""
from __future__ import annotations

import asyncio
from datetime import date, timedelta

from sqlalchemy import select

from app.auth.models import Company
from app.core.db import SessionLocal
from app.core.logging import logger
from app.crawlers.base import DateRange
from app.crawlers.company_ir_rss import CompanyIrRssCrawler
from app.crawlers.fred import FredCrawler
from app.crawlers.mfn import MfnCrawler
from app.crawlers.riksbank import RiksbankCrawler
from app.crawlers.yahoo_finance import YahooFinanceCrawler
from app.engine.drivers.attribution import compute_attribution
from app.engine.drivers.briefing import generate_briefing
from app.ingestion.macro import ingest_macro
from app.ingestion.news import ingest_news
from app.ingestion.prices import ingest_prices


async def backfill(*, days: int = 14) -> None:
    window = DateRange.trailing(days=days)
    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(Company).where(Company.active.is_(True))
            )
        ).scalars().all()
        symbols = [c.yahoo_symbol for c in rows]
        slug_map = {c.mfn_slug: c.ticker for c in rows if c.mfn_slug}
        ir_feeds = [(c.id, c.ir_rss_url) for c in rows if c.ir_rss_url]

        if symbols:
            logger.info("backfill_yahoo", symbols=len(symbols))
            await YahooFinanceCrawler(symbols=symbols).crawl(session, window)
        if slug_map:
            logger.info("backfill_mfn", slugs=len(slug_map))
            await MfnCrawler(slug_to_ticker=slug_map).crawl(session, window)
        logger.info("backfill_riksbank")
        await RiksbankCrawler().crawl(session, window)
        logger.info("backfill_fred")
        await FredCrawler().crawl(session, window)
        if ir_feeds:
            logger.info("backfill_ir_rss", feeds=len(ir_feeds))
            await CompanyIrRssCrawler(feeds=ir_feeds).crawl(session, window)

        logger.info("backfill_ingest")
        await ingest_prices(session)
        await ingest_news(session)
        await ingest_macro(session)
        await session.commit()

        as_of = date.today() - timedelta(days=1)
        for c in rows:
            if c.ticker.startswith("^"):
                continue
            try:
                await compute_attribution(session, company_id=c.id, as_of=as_of)
                await generate_briefing(session, company_id=c.id, as_of=as_of)
                await session.commit()
                logger.info(
                    "backfill_briefing_ok", company=c.ticker, as_of=as_of.isoformat()
                )
            except Exception as e:
                await session.rollback()
                logger.exception(
                    "backfill_briefing_failed",
                    company=c.ticker,
                    as_of=as_of.isoformat(),
                    error=str(e),
                )


def main() -> None:
    asyncio.run(backfill())


if __name__ == "__main__":
    main()
