"""Tier-3 daily attribution computation.

For a given (company_id, as_of), compute and upsert the attribution row:
  return vs benchmark, return vs sector proxy, relative deltas.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import Company
from app.core.config import get_settings
from app.engine.drivers.types import BenchmarkMove, PriceMove, SectorReturn
from app.engine.drivers.tools import (
    BENCHMARK_TICKER,
    get_benchmark_move,
    get_price_move,
    get_sector_proxy_return,
)
from app.engine.models import DailyAttribution


async def compute_attribution(
    session: AsyncSession, *, company_id: int, as_of: date
) -> DailyAttribution | None:
    company = await session.get(Company, company_id)
    if company is None:
        return None

    price_move_res = await get_price_move(
        session=session, company_id=company_id, as_of=as_of
    )
    pm: PriceMove = price_move_res.data
    if pm.daily_return_pct is None:
        return None

    benchmark_present = await session.scalar(
        select(Company).where(Company.yahoo_symbol == BENCHMARK_TICKER)
    )
    bm: BenchmarkMove | None = None
    if benchmark_present is not None:
        bm_res = await get_benchmark_move(session=session, as_of=as_of)
        bm = bm_res.data

    sector_res = await get_sector_proxy_return(
        session=session, company_id=company_id, as_of=as_of
    )
    sr: SectorReturn = sector_res.data

    rel_bench = (
        pm.daily_return_pct - bm.daily_return_pct
        if (bm and bm.daily_return_pct is not None)
        else None
    )
    rel_sect = (
        pm.daily_return_pct - sr.daily_return_pct
        if sr.daily_return_pct is not None
        else None
    )

    existing = await session.scalar(
        select(DailyAttribution).where(
            DailyAttribution.company_id == company_id,
            DailyAttribution.as_of_date == as_of,
        )
    )
    if existing is not None:
        existing.return_pct = pm.daily_return_pct
        existing.benchmark_return_pct = bm.daily_return_pct if bm else None
        existing.sector_return_pct = sr.daily_return_pct
        existing.relative_to_benchmark_pct = rel_bench
        existing.relative_to_sector_pct = rel_sect
        existing.engine_version = get_settings().engine_version
        await session.flush()
        return existing

    row = DailyAttribution(
        company_id=company_id,
        as_of_date=as_of,
        return_pct=pm.daily_return_pct,
        benchmark_return_pct=bm.daily_return_pct if bm else None,
        sector_return_pct=sr.daily_return_pct,
        relative_to_benchmark_pct=rel_bench,
        relative_to_sector_pct=rel_sect,
        engine_version=get_settings().engine_version,
    )
    session.add(row)
    await session.flush()
    return row


_ = Decimal  # keep symmetric with other tools
