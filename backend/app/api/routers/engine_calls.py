from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import any_, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.briefings import EngineCallOut
from app.auth.deps import current_user
from app.auth.models import AppUser, OrgCompanyAccess
from app.chat.models import ChatEngineCall, ChatThread, ChatTurn
from app.core.db import get_session
from app.core.errors import NotFoundError, to_http
from app.engine.ledger import envelope_from_row
from app.engine.models import BriefingCard, EngineCall

router = APIRouter(prefix="/engine_calls", tags=["engine_calls"])


@router.get(
    "/{engine_call_id}",
    response_model=EngineCallOut,
    status_code=status.HTTP_200_OK,
)
async def get_engine_call(
    engine_call_id: str,
    user: AppUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> EngineCallOut:
    # engine_call rows are content-addressed and not tenant-owned; the caller
    # must reach the id through (a) a briefing card on a company in scope, or
    # (b) a chat thread they own. A 404 covers both "not reachable" and "not
    # found" so we don't leak the existence of unreachable ids.
    briefing_match = await session.scalar(
        select(BriefingCard.id)
        .join(OrgCompanyAccess, OrgCompanyAccess.company_id == BriefingCard.company_id)
        .where(
            OrgCompanyAccess.org_id == user.org_id,
            literal(engine_call_id) == any_(BriefingCard.engine_call_ids),
        )
        .limit(1)
    )

    if briefing_match is None:
        chat_match = await session.scalar(
            select(ChatEngineCall.engine_call_id)
            .join(ChatTurn, ChatTurn.id == ChatEngineCall.turn_id)
            .join(ChatThread, ChatThread.id == ChatTurn.thread_id)
            .where(
                ChatThread.org_id == user.org_id,
                ChatEngineCall.engine_call_id == engine_call_id,
            )
            .limit(1)
        )
        if chat_match is None:
            raise to_http(NotFoundError("engine call not found"))

    row = await session.get(EngineCall, engine_call_id)
    if row is None:
        raise to_http(NotFoundError("engine call not found"))
    return EngineCallOut(**envelope_from_row(row))
