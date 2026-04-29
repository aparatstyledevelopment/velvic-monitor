from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.models import PriceBar


async def latest_close_on_or_before(
    session: AsyncSession, *, company_id: int, as_of: date
) -> PriceBar | None:
    return await session.scalar(
        select(PriceBar)
        .where(PriceBar.company_id == company_id, PriceBar.trading_date <= as_of)
        .order_by(desc(PriceBar.trading_date))
        .limit(1)
    )


async def prior_close(
    session: AsyncSession, *, company_id: int, before: date
) -> PriceBar | None:
    return await session.scalar(
        select(PriceBar)
        .where(PriceBar.company_id == company_id, PriceBar.trading_date < before)
        .order_by(desc(PriceBar.trading_date))
        .limit(1)
    )


async def trailing_bars(
    session: AsyncSession, *, company_id: int, as_of: date, days: int
) -> list[PriceBar]:
    rows = (
        await session.execute(
            select(PriceBar)
            .where(
                PriceBar.company_id == company_id,
                PriceBar.trading_date <= as_of,
                PriceBar.trading_date >= as_of - timedelta(days=days * 2),
            )
            .order_by(desc(PriceBar.trading_date))
            .limit(days)
        )
    ).scalars().all()
    return list(reversed(rows))


def daily_return_pct(today: Decimal, prior: Decimal) -> Decimal:
    if prior == 0:
        return Decimal("0.0")
    return ((today - prior) / prior) * Decimal("100")
