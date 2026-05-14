"""End-to-end backfill: crawl + ingest + attribution + briefings.

Runs every step in-process (no Celery dispatch) for the demo seed.
Intended for local development and the first deploy's smoke test.

Run:
    python -m app.admin.backfill              # default 14-day window
    python -m app.admin.backfill --days 60    # longer history

Prints a row-count summary for each step so it's clear what landed in
the database.
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Awaitable, Callable
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select, text
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

# Tables whose row count we sample around each step.
_STEP_TABLES: dict[str, tuple[str, ...]] = {
    "yahoo": ("crawl_run", "yahoo_price_bar"),
    "fred": ("crawl_run", "fred_observation"),
    "ir_rss": ("crawl_run", "company_ir_rss_item"),
    "ingest_prices": ("price_bar",),
    "ingest_news": ("news_item",),
    "ingest_macro": ("macro_observation",),
}


async def _count(session: AsyncSession, table: str) -> int:
    res = await session.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
    val = res.scalar()
    return int(val) if val is not None else 0


async def _snapshot(session: AsyncSession, tables: tuple[str, ...]) -> dict[str, int]:
    return {t: await _count(session, t) for t in tables}


def _format_delta(before: dict[str, int], after: dict[str, int]) -> str:
    parts: list[str] = []
    for table, before_n in before.items():
        delta = after.get(table, before_n) - before_n
        parts.append(f"{table}=+{delta}")
    return "  ".join(parts) if parts else "(no change)"


async def _safe_step(
    session: AsyncSession,
    label: str,
    runner: Callable[[], Awaitable[Any]],
) -> bool:
    tables = _STEP_TABLES.get(label, ())
    before = await _snapshot(session, tables) if tables else {}
    try:
        await runner()
    except Exception as e:  # noqa: BLE001 -- one bad source must not kill the rest
        await session.rollback()
        logger.warning("backfill_step_failed", step=label, error=str(e))
        print(f"{label:17}: FAILED — {e}")
        return False
    await session.commit()
    after = await _snapshot(session, tables) if tables else {}
    summary = _format_delta(before, after) if tables else "ok"
    print(f"{label:17}: {summary}")
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
        tickers = [c.ticker for c in rows]
        symbols = [c.yahoo_symbol for c in rows]
        ir_feeds = [(c.id, c.ir_rss_url) for c in rows if c.ir_rss_url]

        print(
            f"backfill window {window.start.isoformat()} → {window.end.isoformat()} "
            f"({len(rows)} companies: {', '.join(tickers)})"
        )

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
        attributed = 0
        briefed = 0
        for c in rows:
            ticker = c.ticker
            company_id = c.id
            if ticker.startswith("^"):
                continue
            try:
                await compute_attribution(session, company_id=company_id, as_of=as_of)
                attributed += 1
                briefing = await generate_briefing(
                    session, company_id=company_id, as_of=as_of
                )
                briefed += 1
                await session.commit()
                chip_count = len(briefing.smart_chips or [])
                narrative_len = len(briefing.narrative or "")
                print(
                    f"briefing[{ticker} {as_of.isoformat()}]: "
                    f"{narrative_len} chars, {chip_count} chips"
                )
                logger.info(
                    "backfill_briefing_ok",
                    company=ticker,
                    as_of=as_of.isoformat(),
                )
            except Exception as e:
                await session.rollback()
                print(f"briefing[{ticker} {as_of.isoformat()}]: FAILED — {e}")
                logger.exception(
                    "backfill_briefing_failed",
                    company=ticker,
                    as_of=as_of.isoformat(),
                    error=str(e),
                )

        engine_calls_total = await _count(session, "engine_call")
        print(
            f"done. attribution: {attributed}, briefings: {briefed}, "
            f"engine_call rows total: {engine_calls_total}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=14)
    args = parser.parse_args()
    asyncio.run(backfill(days=args.days))


if __name__ == "__main__":
    main()
