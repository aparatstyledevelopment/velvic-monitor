"""Macro ingestion: Riksbank + SCB + FRED -> macro_observation.

Each upstream series is mapped to a stable internal series_code so the
Engine never has to know which source produced a value. The mapping is
explicit and tested.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawlers.models import (
    FredObservation,
    RiksbankObservation,
    ScbObservation,
)
from app.ingestion.models import MacroObservation

# Maps upstream id -> (internal series_code, unit, source label)
RIKSBANK_MAP: dict[str, tuple[str, str]] = {
    "SECBREPOEFF": ("SE.POLICY_RATE", "%"),
    "SEKEURPMI": ("SE.SEK_PER_EUR", "SEK"),
    "SEKUSDPMI": ("SE.SEK_PER_USD", "SEK"),
    "SEKGVB10YC": ("SE.GOVT_10Y_YIELD", "%"),
}

FRED_MAP: dict[str, tuple[str, str]] = {
    "DCOILBRENTEU": ("WORLD.OIL_BRENT", "USD/bbl"),
    "DGS10": ("US.GOVT_10Y_YIELD", "%"),
    "DEXUSEU": ("US.USD_PER_EUR", "USD"),
}


async def ingest_macro(session: AsyncSession, *, since: date | None = None) -> int:
    since = since or (date.today() - timedelta(days=14))
    threshold = datetime.combine(since, datetime.min.time())

    upserted = 0
    upserted += await _ingest_riksbank(session, threshold)
    upserted += await _ingest_fred(session, threshold)
    upserted += await _ingest_scb(session, threshold)
    return upserted


async def _ingest_riksbank(session: AsyncSession, threshold: datetime) -> int:
    rows = (
        (
            await session.execute(
                select(RiksbankObservation).where(
                    RiksbankObservation.fetched_at >= threshold
                )
            )
        )
        .scalars()
        .all()
    )
    return await _promote(
        session, rows, lambda r: RIKSBANK_MAP.get(r.series_id), source="riksbank"
    )


async def _ingest_fred(session: AsyncSession, threshold: datetime) -> int:
    rows = (
        (
            await session.execute(
                select(FredObservation).where(FredObservation.fetched_at >= threshold)
            )
        )
        .scalars()
        .all()
    )
    return await _promote(
        session, rows, lambda r: FRED_MAP.get(r.series_id), source="fred"
    )


async def _ingest_scb(session: AsyncSession, threshold: datetime) -> int:
    rows = (
        (
            await session.execute(
                select(ScbObservation).where(ScbObservation.fetched_at >= threshold)
            )
        )
        .scalars()
        .all()
    )
    upserted = 0
    for r in rows:
        if r.value is None:
            continue
        code = f"SE.{r.table_id}"
        unit = r.unit or "index"
        upserted += await _upsert_one(
            session,
            series_code=code,
            unit=unit,
            obs_date=r.observation_date,
            value=r.value,
            source="scb",
            source_row_id=r.id,
        )
    return upserted


async def _promote(
    session: AsyncSession,
    rows: Sequence[Any],
    map_fn: Callable[[Any], tuple[str, str] | None],
    *,
    source: str,
) -> int:
    upserted = 0
    for r in rows:
        m = map_fn(r)
        if m is None or r.value is None:
            continue
        code, unit = m
        upserted += await _upsert_one(
            session,
            series_code=code,
            unit=unit,
            obs_date=r.observation_date,
            value=r.value,
            source=source,
            source_row_id=r.id,
        )
    return upserted


async def _upsert_one(
    session: AsyncSession,
    *,
    series_code: str,
    unit: str,
    obs_date: date,
    value: Decimal,
    source: str,
    source_row_id: int,
) -> int:
    existing = await session.scalar(
        select(MacroObservation).where(
            MacroObservation.series_code == series_code,
            MacroObservation.observation_date == obs_date,
        )
    )
    if existing is not None:
        if existing.value == value:
            return 0
        existing.value = value
        existing.unit = unit
        existing.source = source
        existing.source_row_id = source_row_id
        return 1
    session.add(
        MacroObservation(
            series_code=series_code,
            observation_date=obs_date,
            value=value,
            unit=unit,
            source=source,
            source_row_id=source_row_id,
        )
    )
    return 1
