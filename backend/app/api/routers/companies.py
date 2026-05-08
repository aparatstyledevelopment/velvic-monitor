from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.companies import CompanyOut
from app.auth.deps import current_user
from app.auth.models import AppUser, Company, OrgCompanyAccess
from app.core.db import get_session

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/companies", response_model=list[CompanyOut])
async def list_my_companies(
    user: AppUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[CompanyOut]:
    rows = (
        await session.execute(
            select(Company, OrgCompanyAccess.is_primary)
            .join(OrgCompanyAccess, OrgCompanyAccess.company_id == Company.id)
            .where(OrgCompanyAccess.org_id == user.org_id)
            .order_by(desc(OrgCompanyAccess.is_primary), Company.ticker)
        )
    ).all()
    return [
        CompanyOut(
            id=c.id,
            ticker=c.ticker,
            name=c.name,
            market=c.market,
            sector=c.sector,
            is_primary=is_primary,
        )
        for c, is_primary in rows
    ]
