from __future__ import annotations

from datetime import date

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.models import MacroObservation


async def latest_value_on_or_before(
    session: AsyncSession, *, series_code: str, as_of: date
) -> MacroObservation | None:
    return await session.scalar(
        select(MacroObservation)
        .where(
            MacroObservation.series_code == series_code,
            MacroObservation.observation_date <= as_of,
        )
        .order_by(desc(MacroObservation.observation_date))
        .limit(1)
    )
