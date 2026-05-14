"""LLM usage summary for the Settings page.

Aggregates `llm_call_log` rows for the caller's org. Rows with NULL
org_id (system pipeline calls — daily briefing composer + news
summaries) are excluded so users see their own org's spend, not the
shared batch cost.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.llm_usage import (
    LLMModelUsage,
    LLMSurfaceUsage,
    LLMUsageSummary,
)
from app.auth.deps import current_user
from app.auth.models import AppUser
from app.chat.models import LLMCallLog
from app.core.db import get_session

router = APIRouter(prefix="/llm/usage", tags=["llm_usage"])


@router.get(
    "/summary",
    response_model=LLMUsageSummary,
    status_code=status.HTTP_200_OK,
)
async def usage_summary(
    user: AppUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> LLMUsageSummary:
    scope = LLMCallLog.org_id == user.org_id

    totals = (
        await session.execute(
            select(
                func.count().label("n"),
                func.coalesce(func.sum(LLMCallLog.prompt_tokens), 0).label("pt"),
                func.coalesce(func.sum(LLMCallLog.completion_tokens), 0).label("ct"),
                func.coalesce(func.sum(LLMCallLog.cost_cents), 0).label("cc"),
            ).where(scope)
        )
    ).one()

    cutoff = datetime.now(UTC) - timedelta(days=30)
    last_30d_cost = (
        await session.scalar(
            select(func.coalesce(func.sum(LLMCallLog.cost_cents), 0)).where(
                scope, LLMCallLog.created_at >= cutoff
            )
        )
    ) or 0

    surface_rows = (
        await session.execute(
            select(
                LLMCallLog.surface,
                func.count().label("n"),
                func.coalesce(func.sum(LLMCallLog.prompt_tokens), 0).label("pt"),
                func.coalesce(func.sum(LLMCallLog.completion_tokens), 0).label("ct"),
                func.coalesce(func.sum(LLMCallLog.cost_cents), 0).label("cc"),
            )
            .where(scope)
            .group_by(LLMCallLog.surface)
            .order_by(func.sum(LLMCallLog.cost_cents).desc())
        )
    ).all()

    model_rows = (
        await session.execute(
            select(
                LLMCallLog.model,
                func.count().label("n"),
                func.coalesce(func.sum(LLMCallLog.prompt_tokens), 0).label("pt"),
                func.coalesce(func.sum(LLMCallLog.completion_tokens), 0).label("ct"),
                func.coalesce(func.sum(LLMCallLog.cost_cents), 0).label("cc"),
            )
            .where(scope)
            .group_by(LLMCallLog.model)
            .order_by(func.sum(LLMCallLog.cost_cents).desc())
        )
    ).all()

    return LLMUsageSummary(
        total_call_count=int(totals.n),
        total_prompt_tokens=int(totals.pt),
        total_completion_tokens=int(totals.ct),
        total_cost_cents=float(totals.cc),
        last_30d_cost_cents=float(last_30d_cost),
        by_surface=[
            LLMSurfaceUsage(
                surface=row.surface,
                call_count=int(row.n),
                prompt_tokens=int(row.pt),
                completion_tokens=int(row.ct),
                cost_cents=float(row.cc),
            )
            for row in surface_rows
        ],
        by_model=[
            LLMModelUsage(
                model=row.model,
                call_count=int(row.n),
                prompt_tokens=int(row.pt),
                completion_tokens=int(row.ct),
                cost_cents=float(row.cc),
            )
            for row in model_rows
        ],
    )
