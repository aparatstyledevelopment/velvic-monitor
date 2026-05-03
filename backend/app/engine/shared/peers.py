from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import Company, PeerRelationship


async def peers_for_company(session: AsyncSession, company_id: int) -> list[Company]:
    rows = (
        (
            await session.execute(
                select(Company)
                .join(
                    PeerRelationship,
                    PeerRelationship.peer_company_id == Company.id,
                )
                .where(PeerRelationship.company_id == company_id)
                .order_by(PeerRelationship.rank)
            )
        )
        .scalars()
        .all()
    )
    return list(rows)
