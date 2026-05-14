"""Per-call LLM logging — overview only, no payloads.

One row per Claude call (SDK turn or single-shot Messages call). The
Settings page sums these rows for the user's org; finops drills into
them for cost attribution. Sensitive payloads (prompts, responses,
tool inputs) are intentionally NOT stored.

Logging is best-effort: a failed insert never aborts the surface that
made the LLM call. We catch+log and move on.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import LLMCallLog
from app.core.logging import logger

Surface = Literal[
    "chat_orchestrator",
    "chat_orchestrator_retry",
    "topic_gate",
    "thread_title",
    "briefing_narrative",
    "news_summary",
]

Transport = Literal["sdk", "messages_api"]


@dataclass(frozen=True)
class LLMCallStats:
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_cents: float
    latency_ms: int | None = None


@dataclass(frozen=True)
class LLMLogContext:
    """Caller scope. All optional — system pipeline calls pass org=None."""

    org_id: UUID | None = None
    user_id: UUID | None = None
    thread_id: UUID | None = None
    company_id: int | None = None


async def record_call(
    session: AsyncSession,
    *,
    surface: Surface,
    transport: Transport,
    stats: LLMCallStats,
    ctx: LLMLogContext,
) -> None:
    """Persist one llm_call_log row. Best-effort: never raises."""
    try:
        row = LLMCallLog(
            org_id=ctx.org_id,
            user_id=ctx.user_id,
            thread_id=ctx.thread_id,
            company_id=ctx.company_id,
            surface=surface,
            transport=transport,
            model=stats.model,
            prompt_tokens=stats.prompt_tokens,
            completion_tokens=stats.completion_tokens,
            cost_cents=Decimal(str(round(stats.cost_cents, 4))),
            latency_ms=stats.latency_ms,
        )
        session.add(row)
        await session.flush()
    except SQLAlchemyError as e:
        logger.warning(
            "llm_call_log_failed",
            surface=surface,
            transport=transport,
            error=str(e),
        )
