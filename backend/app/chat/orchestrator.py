"""Chat orchestrator.

Drives one user turn end-to-end:

  load thread -> persist user turn -> topic gate -> tool loop (<= 8 calls)
  -> citation parse -> strict retry on uncited -> persist assistant turn

Yields CompletionEvent objects so the API layer can render them as SSE
without knowing anything about the orchestrator's internal state.

The tool loop uses provider.complete() per iteration; per-token streaming
inside a single LLM call is a future enhancement (the provider already
exposes stream_complete()). The orchestrator emits text_delta events
synthetically so the SSE wire format is identical either way.

Citation discipline:
- Non-final assistant text (preceding tool calls) streams immediately.
- Final assistant text is held back until parse_citations + uncited check.
- If uncited, a strict-prompt retry runs once; the retry result is what
  reaches the user. If retry still has uncited numbers, a `warning` event
  is emitted alongside the (best-effort) text.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import AppUser, Company, Org, OrgCompanyAccess
from app.chat import topic_gate as topic_gate_mod
from app.chat.citations import find_uncited_numerics, parse_citations
from app.chat.models import ChatEngineCall, ChatThread, ChatTurn
from app.chat.prompts import CHAT_SYSTEM_PROMPT, CHAT_SYSTEM_PROMPT_STRICT
from app.chat.providers.base import (
    CompletionEvent,
    LLMProvider,
    Message,
    ToolCall,
)
from app.chat.providers.factory import get_provider
from app.chat.tools import (
    ToolArgumentError,
    UnknownToolError,
    dispatch,
    tool_specs_for_chat,
)
from app.core.config import get_settings
from app.core.errors import ForbiddenError, NotFoundError
from app.core.logging import logger

MAX_TOOL_CALLS = 8
DEFAULT_TOOL_MODULES = ("drivers", "shared")
HISTORY_LIMIT = 20  # most-recent N turns sent back to the model

ProviderFactory = Callable[[Org], LLMProvider]


@dataclass
class _TurnState:
    """Mutable state accumulated across tool-loop iterations."""

    messages: list[Message]
    engine_call_ids: list[str]
    tool_call_count: int
    prompt_tokens: int
    completion_tokens: int
    cost_cents: float
    model: str
    provider_name: str
    finish_reason: str


class ChatOrchestrator:
    def __init__(
        self,
        *,
        provider_factory: ProviderFactory | None = None,
        gate_provider_factory: ProviderFactory | None = None,
        tool_modules: tuple[str, ...] = DEFAULT_TOOL_MODULES,
    ) -> None:
        self._provider_factory = provider_factory or _default_provider_factory
        self._gate_provider_factory = gate_provider_factory or _default_provider_factory
        self._tool_modules = tool_modules

    async def process_turn(
        self,
        *,
        thread_id: UUID,
        user_message: str,
        session: AsyncSession,
        user: AppUser,
    ) -> AsyncGenerator[CompletionEvent, None]:
        """Drive a turn and return an async iterator of CompletionEvents."""
        return _drive_turn(self, thread_id, user_message, session, user)


# ---------------------------------------------------------------------- driver


async def _drive_turn(
    orch: ChatOrchestrator,
    thread_id: UUID,
    user_message: str,
    session: AsyncSession,
    user: AppUser,
) -> AsyncGenerator[CompletionEvent, None]:
    thread = await _load_thread(session, thread_id, user)
    company = await session.get(Company, thread.company_id)
    if company is None:
        raise NotFoundError("thread company missing")
    org = await session.get(Org, user.org_id)
    if org is None:
        raise NotFoundError("org missing")

    # Persist the user turn first so it survives any downstream failure.
    next_idx = await _next_idx(session, thread_id)
    user_turn = ChatTurn(
        thread_id=thread_id,
        idx=next_idx,
        role="user",
        content=user_message,
    )
    session.add(user_turn)
    await session.flush()

    gate_provider = orch._gate_provider_factory(org)
    decision = await topic_gate_mod.classify(gate_provider, user_message)
    if not decision.on_topic:
        refusal = topic_gate_mod.render_refusal(
            company_name=company.name, reason=decision.reason
        )
        async for ev in _persist_and_emit_refusal(
            session=session,
            thread=thread,
            refusal=refusal,
        ):
            yield ev
        return

    provider = orch._provider_factory(org)
    tools = tool_specs_for_chat(list(orch._tool_modules))
    history = await _build_history(session, thread_id, exclude_turn_id=user_turn.id)
    state = _TurnState(
        messages=history + [Message(role="user", content=user_message)],
        engine_call_ids=[],
        tool_call_count=0,
        prompt_tokens=0,
        completion_tokens=0,
        cost_cents=0.0,
        model="",
        provider_name="",
        finish_reason="stop",
    )

    final_text = ""

    # Tool loop. Each iteration may dispatch zero or more tool calls.
    while True:
        active_tools = tools if state.tool_call_count < MAX_TOOL_CALLS else None
        result = await provider.complete(
            system=CHAT_SYSTEM_PROMPT,
            messages=state.messages,
            tools=active_tools,
            max_tokens=2048,
            temperature=0.2,
        )
        state.prompt_tokens += result.prompt_tokens
        state.completion_tokens += result.completion_tokens
        state.cost_cents += result.cost_cents
        state.model = result.model
        state.provider_name = result.provider
        state.finish_reason = result.finish_reason

        if result.tool_calls and state.tool_call_count < MAX_TOOL_CALLS:
            # Non-final iteration: stream any banter and the tool calls.
            if result.text:
                yield CompletionEvent(type="text_delta", payload={"text": result.text})
            state.messages.append(
                Message(
                    role="assistant",
                    content=result.text,
                    tool_calls=list(result.tool_calls),
                )
            )

            for call in result.tool_calls:
                async for ev in _execute_tool_call(call, session=session, state=state):
                    yield ev

            continue

        # Final iteration. Hold the text until citation discipline runs.
        final_text = result.text
        break

    valid_ids = set(state.engine_call_ids)
    parsed = parse_citations(final_text, valid_ids)
    uncited = find_uncited_numerics(parsed.text, parsed.spans)
    warning_code: str | None = None

    if uncited:
        logger.warning(
            "chat_uncited_numerics_pre_retry",
            thread_id=str(thread_id),
            count=len(uncited),
        )
        retry = await provider.complete(
            system=CHAT_SYSTEM_PROMPT_STRICT,
            messages=state.messages,
            tools=None,
            max_tokens=1024,
            temperature=0.0,
        )
        state.prompt_tokens += retry.prompt_tokens
        state.completion_tokens += retry.completion_tokens
        state.cost_cents += retry.cost_cents
        state.finish_reason = retry.finish_reason
        retry_parsed = parse_citations(retry.text, valid_ids)
        retry_uncited = find_uncited_numerics(retry_parsed.text, retry_parsed.spans)
        if retry_uncited:
            warning_code = "uncited_numeric"
            parsed = retry_parsed
        else:
            parsed = retry_parsed

    final_text = parsed.text

    # Stream the final text and persist.
    if final_text:
        yield CompletionEvent(type="text_delta", payload={"text": final_text})

    if warning_code is not None:
        yield CompletionEvent(
            type="warning",
            payload={
                "code": warning_code,
                "message": "response contains numbers without citations; review carefully",
            },
        )

    assistant_idx = await _next_idx(session, thread_id)
    assistant_turn = ChatTurn(
        thread_id=thread_id,
        idx=assistant_idx,
        role="assistant",
        content=final_text,
        citation_spans=[
            {
                "start_char": s.start_char,
                "end_char": s.end_char,
                "engine_call_id": s.engine_call_id,
            }
            for s in parsed.spans
        ],
        llm_provider=state.provider_name,
        llm_model=state.model,
        prompt_tokens=state.prompt_tokens,
        completion_tokens=state.completion_tokens,
        cost_cents=Decimal(str(round(state.cost_cents, 4))),
        finish_reason=state.finish_reason,
        warning=warning_code,
    )
    session.add(assistant_turn)
    await session.flush()
    for ec_id in dict.fromkeys(state.engine_call_ids):
        session.add(ChatEngineCall(turn_id=assistant_turn.id, engine_call_id=ec_id))
    thread.updated_at = datetime.now(UTC)
    await session.commit()

    yield CompletionEvent(
        type="done",
        payload={
            "turn_id": str(assistant_turn.id),
            "thread_id": str(thread_id),
            "finish_reason": state.finish_reason,
            "prompt_tokens": state.prompt_tokens,
            "completion_tokens": state.completion_tokens,
            "cost_cents": round(state.cost_cents, 4),
            "model": state.model,
            "provider": state.provider_name,
            "engine_call_ids": list(dict.fromkeys(state.engine_call_ids)),
        },
    )


async def _execute_tool_call(
    call: ToolCall,
    *,
    session: AsyncSession,
    state: _TurnState,
) -> AsyncGenerator[CompletionEvent, None]:
    yield CompletionEvent(
        type="tool_call",
        payload={"id": call.id, "name": call.name, "arguments": call.arguments},
    )
    try:
        result = await dispatch(call, session=session)
    except (UnknownToolError, ToolArgumentError) as e:
        err_msg = str(e)
        logger.warning("chat_tool_error", tool=call.name, error=err_msg)
        state.messages.append(
            Message(
                role="tool",
                content=json.dumps({"error": err_msg}),
                tool_call_id=call.id,
                tool_name=call.name,
            )
        )
        state.tool_call_count += 1
        yield CompletionEvent(
            type="tool_result",
            payload={"tool_call_id": call.id, "error": err_msg},
        )
        return

    state.engine_call_ids.append(result.engine_call_id)
    state.messages.append(
        Message(
            role="tool",
            content=result.envelope_json,
            tool_call_id=call.id,
            tool_name=call.name,
        )
    )
    state.tool_call_count += 1
    yield CompletionEvent(
        type="tool_result",
        payload={
            "tool_call_id": call.id,
            "engine_call_id": result.engine_call_id,
            "tool_name": call.name,
        },
    )


async def _persist_and_emit_refusal(
    *, session: AsyncSession, thread: ChatThread, refusal: str
) -> AsyncGenerator[CompletionEvent, None]:
    next_idx = await _next_idx(session, thread.id)
    assistant_turn = ChatTurn(
        thread_id=thread.id,
        idx=next_idx,
        role="assistant",
        content=refusal,
        finish_reason="refusal",
    )
    session.add(assistant_turn)
    await session.flush()
    thread.updated_at = datetime.now(UTC)
    await session.commit()
    yield CompletionEvent(type="text_delta", payload={"text": refusal})
    yield CompletionEvent(
        type="done",
        payload={
            "turn_id": str(assistant_turn.id),
            "thread_id": str(thread.id),
            "finish_reason": "refusal",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cost_cents": 0.0,
            "model": "",
            "provider": "",
            "engine_call_ids": [],
        },
    )


# ---------------------------------------------------------------------- helpers


async def _load_thread(
    session: AsyncSession, thread_id: UUID, user: AppUser
) -> ChatThread:
    thread = await session.get(ChatThread, thread_id)
    if thread is None or thread.org_id != user.org_id:
        raise NotFoundError("thread not found")
    if thread.user_id != user.id:
        raise ForbiddenError("thread not owned by user")
    access = await session.scalar(
        select(OrgCompanyAccess).where(
            OrgCompanyAccess.org_id == user.org_id,
            OrgCompanyAccess.company_id == thread.company_id,
        )
    )
    if access is None:
        raise ForbiddenError("thread company not in scope for org")
    return thread


async def _next_idx(session: AsyncSession, thread_id: UUID) -> int:
    current = await session.scalar(
        select(func.max(ChatTurn.idx)).where(ChatTurn.thread_id == thread_id)
    )
    return (current or 0) + 1


async def _build_history(
    session: AsyncSession, thread_id: UUID, *, exclude_turn_id: UUID | None
) -> list[Message]:
    rows = (
        (
            await session.execute(
                select(ChatTurn)
                .where(ChatTurn.thread_id == thread_id)
                .order_by(desc(ChatTurn.idx))
                .limit(HISTORY_LIMIT)
            )
        )
        .scalars()
        .all()
    )
    msgs: list[Message] = []
    for row in reversed(rows):
        if exclude_turn_id is not None and row.id == exclude_turn_id:
            continue
        if row.role == "user":
            msgs.append(Message(role="user", content=row.content))
        elif row.role == "assistant":
            msgs.append(Message(role="assistant", content=row.content))
        elif row.role == "tool" and row.tool_call_id is not None:
            msgs.append(
                Message(
                    role="tool",
                    content=row.content,
                    tool_call_id=row.tool_call_id,
                    tool_name=row.tool_name,
                )
            )
    return msgs


def _default_provider_factory(org: Org) -> LLMProvider:
    """Pick a provider for `org`. Falls back to mock when no API key."""
    settings = get_settings()
    pref = (org.llm_provider_pref or "anthropic").lower()
    if pref == "anthropic":
        if settings.anthropic_api_key:
            return get_provider("anthropic")
        return get_provider("mock")
    # OpenAI/Google providers are not implemented in v1 yet; fall back.
    if settings.anthropic_api_key:
        return get_provider("anthropic")
    return get_provider("mock")
