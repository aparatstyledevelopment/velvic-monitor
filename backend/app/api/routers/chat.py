from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.chat import (
    ChatThreadCreate,
    ChatThreadDetail,
    ChatThreadOut,
    ChatTurnIn,
    ChatTurnOut,
    CitationSpanOut,
)
from app.auth.deps import current_user
from app.auth.models import AppUser, Company, OrgCompanyAccess
from app.chat.models import ChatThread, ChatTurn
from app.chat.orchestrator import ChatOrchestrator
from app.core.db import get_session
from app.core.errors import ForbiddenError, NotFoundError, to_http
from app.core.streaming import sse_response

router = APIRouter(prefix="/chat", tags=["chat"])

_orchestrator = ChatOrchestrator()


async def _ensure_company_access(
    session: AsyncSession, *, user: AppUser, company_id: int
) -> Company:
    company = await session.get(Company, company_id)
    if company is None:
        raise to_http(NotFoundError("company not found"))
    access = await session.scalar(
        select(OrgCompanyAccess).where(
            OrgCompanyAccess.org_id == user.org_id,
            OrgCompanyAccess.company_id == company_id,
        )
    )
    if access is None:
        raise to_http(NotFoundError("company not in scope for org"))
    return company


@router.post(
    "/threads",
    response_model=ChatThreadOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_thread(
    body: ChatThreadCreate,
    user: AppUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> ChatThreadOut:
    company = await _ensure_company_access(
        session, user=user, company_id=body.company_id
    )
    title = body.title or f"Conversation about {company.ticker}"
    thread = ChatThread(
        org_id=user.org_id,
        user_id=user.id,
        company_id=body.company_id,
        title=title[:200],
    )
    session.add(thread)
    await session.flush()
    await session.commit()
    return _thread_out(thread)


@router.get(
    "/threads",
    response_model=list[ChatThreadOut],
)
async def list_threads(
    user: AppUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ChatThreadOut]:
    rows = (
        (
            await session.execute(
                select(ChatThread)
                .where(
                    ChatThread.org_id == user.org_id,
                    ChatThread.user_id == user.id,
                    ChatThread.is_archived.is_(False),
                )
                .order_by(desc(ChatThread.updated_at))
                .limit(100)
            )
        )
        .scalars()
        .all()
    )
    return [_thread_out(t) for t in rows]


@router.get(
    "/threads/{thread_id}",
    response_model=ChatThreadDetail,
)
async def get_thread(
    thread_id: UUID,
    user: AppUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> ChatThreadDetail:
    thread = await session.get(ChatThread, thread_id)
    if thread is None or thread.org_id != user.org_id:
        raise to_http(NotFoundError("thread not found"))
    if thread.user_id != user.id:
        raise to_http(ForbiddenError("thread not owned by user"))
    turn_rows = (
        (
            await session.execute(
                select(ChatTurn)
                .where(ChatTurn.thread_id == thread_id)
                .order_by(ChatTurn.idx)
            )
        )
        .scalars()
        .all()
    )
    return ChatThreadDetail(
        **_thread_out(thread).model_dump(),
        turns=[_turn_out(t) for t in turn_rows],
    )


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_thread(
    thread_id: UUID,
    user: AppUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    thread = await session.get(ChatThread, thread_id)
    if thread is None or thread.org_id != user.org_id or thread.user_id != user.id:
        raise to_http(NotFoundError("thread not found"))
    thread.is_archived = True
    thread.updated_at = datetime.now(UTC)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/threads/{thread_id}/turns",
    response_class=StreamingResponse,
)
async def post_turn(
    thread_id: UUID,
    body: ChatTurnIn,
    user: AppUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    iterator = await _orchestrator.process_turn(
        thread_id=thread_id,
        user_message=body.message,
        session=session,
        user=user,
    )
    return sse_response(iterator)


# -------------------------------------------------------------- serialization


def _thread_out(t: ChatThread) -> ChatThreadOut:
    return ChatThreadOut(
        id=t.id,
        company_id=t.company_id,
        user_id=t.user_id,
        title=t.title,
        is_archived=t.is_archived,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


def _turn_out(t: ChatTurn) -> ChatTurnOut:
    spans = [
        CitationSpanOut(
            start_char=s.get("start_char", 0),
            end_char=s.get("end_char", 0),
            engine_call_id=s.get("engine_call_id", ""),
        )
        for s in (t.citation_spans or [])
    ]
    return ChatTurnOut(
        id=t.id,
        thread_id=t.thread_id,
        idx=t.idx,
        role=t.role,
        content=t.content,
        tool_calls=t.tool_calls,
        tool_call_id=t.tool_call_id,
        tool_name=t.tool_name,
        citation_spans=spans,
        llm_provider=t.llm_provider,
        llm_model=t.llm_model,
        prompt_tokens=t.prompt_tokens,
        completion_tokens=t.completion_tokens,
        cost_cents=t.cost_cents,
        finish_reason=t.finish_reason,
        warning=t.warning,
        created_at=t.created_at,
    )
