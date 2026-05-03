from __future__ import annotations

from datetime import date as Date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.briefings import BriefingOut, EngineCallOut
from app.auth.deps import current_user
from app.auth.models import AppUser, OrgCompanyAccess
from app.core.db import get_session
from app.core.errors import NotFoundError, to_http
from app.engine.ledger import envelope_from_row
from app.engine.models import BriefingCard, EngineCall

router = APIRouter(prefix="/companies", tags=["briefings"])


async def _ensure_access(
    session: AsyncSession, *, user: AppUser, company_id: int
) -> None:
    access = await session.scalar(
        select(OrgCompanyAccess).where(
            OrgCompanyAccess.org_id == user.org_id,
            OrgCompanyAccess.company_id == company_id,
        )
    )
    if access is None:
        raise to_http(NotFoundError("company not in scope for org"))


@router.get(
    "/{company_id}/briefings/latest",
    response_model=BriefingOut,
    status_code=status.HTTP_200_OK,
)
async def latest_briefing(
    company_id: int,
    user: AppUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> BriefingOut:
    await _ensure_access(session, user=user, company_id=company_id)
    row = await session.scalar(
        select(BriefingCard)
        .where(BriefingCard.company_id == company_id, BriefingCard.module == "drivers")
        .order_by(desc(BriefingCard.as_of_date))
        .limit(1)
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "no_briefing", "message": "no briefing available"},
        )
    return _to_out(row)


@router.get(
    "/{company_id}/briefings/{date}",
    response_model=BriefingOut,
)
async def briefing_for_date(
    company_id: int,
    date: Date,
    user: AppUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> BriefingOut:
    await _ensure_access(session, user=user, company_id=company_id)
    row = await session.scalar(
        select(BriefingCard).where(
            BriefingCard.company_id == company_id,
            BriefingCard.module == "drivers",
            BriefingCard.as_of_date == date,
        )
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "no_briefing", "message": "no briefing for that date"},
        )
    return _to_out(row)


@router.get(
    "/{company_id}/briefings/{date}/evidence",
    response_model=list[EngineCallOut],
)
async def briefing_evidence(
    company_id: int,
    date: Date,
    user: AppUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[EngineCallOut]:
    await _ensure_access(session, user=user, company_id=company_id)
    row = await session.scalar(
        select(BriefingCard).where(
            BriefingCard.company_id == company_id,
            BriefingCard.module == "drivers",
            BriefingCard.as_of_date == date,
        )
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "no_briefing", "message": "no briefing for that date"},
        )
    calls = (
        (
            await session.execute(
                select(EngineCall).where(EngineCall.id.in_(row.engine_call_ids))
            )
        )
        .scalars()
        .all()
    )
    return [EngineCallOut(**envelope_from_row(c)) for c in calls]


def _to_out(row: BriefingCard) -> BriefingOut:
    return BriefingOut(
        company_id=row.company_id,
        module=row.module,
        as_of_date=row.as_of_date,
        narrative=row.narrative,
        smart_chips=list(row.smart_chips) if isinstance(row.smart_chips, list) else [],
        citation_spans=[
            {
                "start_char": s.get("start_char", 0),
                "end_char": s.get("end_char", 0),
                "engine_call_id": s.get("engine_call_id", ""),
            }
            for s in (row.citation_spans or [])
        ],
        engine_call_ids=list(row.engine_call_ids or []),
        llm_provider=row.llm_provider,
        llm_model=row.llm_model,
        prompt_tokens=row.prompt_tokens,
        completion_tokens=row.completion_tokens,
        cost_cents=row.cost_cents,
        generated_at=row.generated_at,
    )
