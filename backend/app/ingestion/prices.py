"""Yahoo raw bars -> curated price_bar rows.

Idempotent: re-running on the same window upserts only when content
differs, never on natural primary key alone.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import Company
from app.crawlers.models import YahooPriceBar
from app.ingestion.models import PriceBar


async def ingest_prices(session: AsyncSession, *, since: date | None = None) -> int:
    """Promote new yahoo_price_bar rows to price_bar.

    `since` defaults to the prior 7 days; pass a wider window for backfill.
    """
    since = since or (date.today() - timedelta(days=7))
    threshold = datetime.combine(since, datetime.min.time())

    yahoo_rows = (
        await session.execute(
            select(YahooPriceBar)
            .where(YahooPriceBar.fetched_at >= threshold)
            .where(YahooPriceBar.superseded_by.is_(None))
        )
    ).scalars().all()

    upserted = 0
    for raw in yahoo_rows:
        company = await _company_for_yahoo_symbol(session, raw.ticker)
        if company is None:
            continue
        if raw.close is None:
            continue
        existing = await session.scalar(
            select(PriceBar).where(
                PriceBar.company_id == company.id,
                PriceBar.trading_date == raw.trading_date,
            )
        )
        if existing is not None:
            if (
                existing.close == raw.close
                and existing.volume == raw.volume
                and existing.adj_close == raw.adj_close
            ):
                continue
            existing.open = raw.open
            existing.high = raw.high
            existing.low = raw.low
            existing.close = raw.close
            existing.adj_close = raw.adj_close
            existing.volume = raw.volume
            existing.source_row_id = raw.id
            upserted += 1
            continue
        session.add(
            PriceBar(
                company_id=company.id,
                trading_date=raw.trading_date,
                open=raw.open,
                high=raw.high,
                low=raw.low,
                close=cast("Decimal", raw.close),
                adj_close=raw.adj_close,
                volume=raw.volume,
                source="yahoo",
                source_row_id=raw.id,
            )
        )
        upserted += 1
    await session.flush()
    return upserted


async def _company_for_yahoo_symbol(
    session: AsyncSession, symbol: str
) -> Company | None:
    return await session.scalar(
        select(Company).where(Company.yahoo_symbol == symbol)
    )


# Decimal needed by cast() above; keep import in module form for clarity.
from decimal import Decimal as _Decimal  # noqa: E402

_ = _Decimal
