"""End-to-end backfill: crawl + ingest + attribution + briefings.

Runs every step in-process (no Celery dispatch) for the demo seed.
Intended for local development and the first deploy's smoke test.

Run: `python -m app.admin.backfill`
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import Company
from app.core.db import SessionLocal
from app.core.logging import logger
from app.crawlers.base import DateRange
from app.crawlers.company_ir_rss import CompanyIrRssCrawler
from app.crawlers.fred import FredCrawler
from app.crawlers.yahoo_finance import YahooFinanceCrawler
from app.engine.drivers.attribution import compute_attribution
from app.engine.drivers.briefing import generate_briefing
from app.ingestion.macro import ingest_macro
from app.ingestion.news import ingest_news
from app.ingestion.prices import ingest_prices


async def _safe_step(
    session: AsyncSession, label: str, runner: Callable[[], Awaitable[Any]]
) -> bool:
    try:
        await runner()
    except Exception as e:  # noqa: BLE001 -- one bad source must not kill the rest
        await session.rollback()
        logger.warning("backfill_step_failed", step=label, error=str(e))
        return False
    await session.commit()
    logger.info("backfill_step_ok", step=label)
    return True


async def backfill(*, days: int = 14) -> None:
    window = DateRange.trailing(days=days)
    async with SessionLocal() as session:
        rows = (
            (await session.execute(select(Company).where(Company.active.is_(True))))
            .scalars()
            .all()
        )
        symbols = [c.yahoo_symbol for c in rows]
        ir_feeds = [(c.id, c.ir_rss_url) for c in rows if c.ir_rss_url]

        if symbols:
            await _safe_step(
                session,
                "yahoo",
                lambda: YahooFinanceCrawler(symbols=symbols).crawl(session, window),
            )
        await _safe_step(session, "fred", lambda: FredCrawler().crawl(session, window))
        if ir_feeds:
            await _safe_step(
                session,
                "ir_rss",
                lambda: CompanyIrRssCrawler(feeds=ir_feeds).crawl(session, window),
            )

        await _safe_step(session, "ingest_prices", lambda: ingest_prices(session))
        await _safe_step(session, "ingest_news", lambda: ingest_news(session))
        await _safe_step(session, "ingest_macro", lambda: ingest_macro(session))

        as_of = date.today() - timedelta(days=1)
        for c in rows:
            # Snapshot identifying attrs before any session.rollback() — a
            # rollback expires SA attributes, and a later c.ticker access in
            # the except handler triggers a sync lazy-load that fails with
            # MissingGreenlet inside the asyncio loop.
            ticker = c.ticker
            company_id = c.id
            if ticker.startswith("^"):
                continue
            try:
                await compute_attribution(session, company_id=company_id, as_of=as_of)
                await generate_briefing(session, company_id=company_id, as_of=as_of)
                await session.commit()
                logger.info(
                    "backfill_briefing_ok", company=ticker, as_of=as_of.isoformat()
                )
            except Exception as e:
                await session.rollback()
                logger.exception(
                    "backfill_briefing_failed",
                    company=ticker,
                    as_of=as_of.isoformat(),
                    error=str(e),
                )


def main() -> None:
    asyncio.run(backfill())


if __name__ == "__main__":
    main()
