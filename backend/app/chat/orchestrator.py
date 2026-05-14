"""Chat orchestrator.

Drives one user turn end-to-end:

  load thread -> persist user turn -> topic gate -> SDK tool loop (<= 8 calls)
  -> citation parse -> strict retry on uncited -> persist assistant turn

The agent loop is owned by the Claude Agent SDK (ADR 0009). Engine tools
are exposed to it through an in-process MCP server built fresh per turn
so each tool handler can close over the request's AsyncSession. The
PostToolUse hook captures `engine_call_id`s from each tool envelope so
citation parsing can validate the final assistant text against them.

Citation discipline:
- The orchestrator accumulates the final assistant text from the SDK's
  AssistantMessage stream. After the stream ends, it runs `parse_citations`
  + `find_uncited_numerics`.
- If uncited, a second SDK `query()` runs with the strict system prompt
  and no tools; the retry result is what reaches the user. If retry still
  has uncited numbers, a `warning` event is emitted alongside the text.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    HookMatcher,
    Message as SDKMessage,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import AppUser, Company, Org, OrgCompanyAccess
from app.chat import followups as followups_mod
from app.chat import thread_title as thread_title_mod
from app.chat import topic_gate as topic_gate_mod
from app.chat.anthropic_messages_client import (
    DEFAULT_MODEL,
    PRICING_CENTS_PER_MTOK,
    cost_cents,
)
from app.chat.citations import find_uncited_numerics, parse_citations
from app.chat.llm_log import LLMCallStats, LLMLogContext, record_call
from app.chat.models import ChatEngineCall, ChatThread, ChatTurn
from app.chat.prompts import render_chat_system_prompt
from app.chat.sdk_hooks import TurnHookState, make_post_tool_use_hook
from app.chat.sdk_mcp import (
    allowed_tool_names,
    build_engine_mcp_server,
    strip_mcp_prefix,
)
from app.chat.topic_gate import ClassifyResult, TopicDecision
from app.chat.types import CompletionEvent
from app.core.errors import ForbiddenError, NotFoundError
from app.core.logging import logger

MAX_TOOL_CALLS = 8
DEFAULT_TOOL_MODULES = ("drivers", "shared")
HISTORY_LIMIT = 20  # most-recent N turns sent back to the model

ClientFactory = Callable[[ClaudeAgentOptions], ClaudeSDKClient]
GateClassifyFn = Callable[..., Awaitable[ClassifyResult]]


@dataclass
class _TurnState:
    """Mutable state accumulated across the SDK message stream."""

    hooks: TurnHookState
    final_text: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_cents_total: float = 0.0
    model: str = ""
    finish_reason: str = "stop"
    fallback_text_parts: list[str] = field(default_factory=list)


class ChatOrchestrator:
    def __init__(
        self,
        *,
        client_factory: ClientFactory | None = None,
        gate_classify_fn: GateClassifyFn | None = None,
        tool_modules: tuple[str, ...] = DEFAULT_TOOL_MODULES,
    ) -> None:
        self._client_factory = client_factory or _default_client_factory
        self._gate_classify_fn = gate_classify_fn or topic_gate_mod.classify
        self._tool_modules = tool_modules

    async def process_turn(
        self,
        *,
        thread_id: UUID,
        user_message: str,
        session: AsyncSession,
        user: AppUser,
        bypass_topic_gate: bool = False,
    ) -> AsyncGenerator[CompletionEvent, None]:
        """Drive a turn and return an async iterator of CompletionEvents.

        `bypass_topic_gate` is a demo-only escape hatch surfaced through the
        Settings page; when true the topic-gate refusal path is skipped and
        every prompt reaches the model.
        """
        return _drive_turn(
            self, thread_id, user_message, session, user, bypass_topic_gate
        )


# ---------------------------------------------------------------------- driver


async def _drive_turn(
    orch: ChatOrchestrator,
    thread_id: UUID,
    user_message: str,
    session: AsyncSession,
    user: AppUser,
    bypass_topic_gate: bool = False,
) -> AsyncGenerator[CompletionEvent, None]:
    thread = await _load_thread(session, thread_id, user)
    company = await session.get(Company, thread.company_id)
    if company is None:
        raise NotFoundError("thread company missing")
    org = await session.get(Org, user.org_id)
    if org is None:
        raise NotFoundError("org missing")

    next_idx = await _next_idx(session, thread_id)
    user_turn = ChatTurn(
        thread_id=thread_id,
        idx=next_idx,
        role="user",
        content=user_message,
    )
    session.add(user_turn)
    await session.flush()

    if bypass_topic_gate:
        logger.info(
            "chat_topic_gate_bypassed",
            thread_id=str(thread_id),
            user_id=str(user.id),
        )
    else:
        gate_result = await orch._gate_classify_fn(
            user_message,
            company_name=company.name,
            ticker=company.ticker,
        )
        decision = gate_result.decision
        if gate_result.response is not None:
            await record_call(
                session,
                surface="topic_gate",
                transport="messages_api",
                stats=LLMCallStats(
                    model=gate_result.response.model,
                    prompt_tokens=gate_result.response.prompt_tokens,
                    completion_tokens=gate_result.response.completion_tokens,
                    cost_cents=gate_result.response.cost_cents,
                ),
                ctx=LLMLogContext(
                    org_id=org.id,
                    user_id=user.id,
                    thread_id=thread_id,
                    company_id=company.id,
                ),
            )
        if not decision.on_topic:
            refusal = topic_gate_mod.render_refusal(
                company_name=company.name, reason=decision.reason
            )
            async for ev in _persist_and_emit_refusal(
                session=session, thread=thread, refusal=refusal
            ):
                yield ev
            return

    tool_modules = list(orch._tool_modules)
    history = await _build_history(session, thread_id, exclude_turn_id=user_turn.id)
    today = date.today()
    system_prompt = render_chat_system_prompt(
        company_name=company.name,
        ticker=company.ticker,
        company_id=company.id,
        today=today,
    )
    strict_system_prompt = render_chat_system_prompt(
        company_name=company.name,
        ticker=company.ticker,
        company_id=company.id,
        today=today,
        strict=True,
    )
    composed_system = _compose_system_prompt(system_prompt, history)

    state = _TurnState(hooks=TurnHookState())
    options = _build_options(
        session=session,
        modules=tool_modules,
        system_prompt=composed_system,
        state=state,
    )

    log_ctx = LLMLogContext(
        org_id=org.id,
        user_id=user.id,
        thread_id=thread_id,
        company_id=company.id,
    )

    client = orch._client_factory(options)
    async with client:
        await client.query(user_message)
        async for msg in client.receive_response():
            async for ev in _events_from_sdk_message(msg, state):
                yield ev

    await record_call(
        session,
        surface="chat_orchestrator",
        transport="sdk",
        stats=LLMCallStats(
            model=state.model or DEFAULT_MODEL,
            prompt_tokens=state.prompt_tokens,
            completion_tokens=state.completion_tokens,
            cost_cents=state.cost_cents_total,
        ),
        ctx=log_ctx,
    )

    final_text = state.final_text or "".join(state.fallback_text_parts)
    valid_ids = set(state.hooks.engine_call_ids)
    parsed = parse_citations(final_text, valid_ids)
    uncited = find_uncited_numerics(parsed.text, parsed.spans)
    warning_code: str | None = None

    if uncited:
        logger.warning(
            "chat_uncited_numerics_pre_retry",
            thread_id=str(thread_id),
            count=len(uncited),
        )
        retry_state = _TurnState(hooks=TurnHookState())
        retry_composed_system = _compose_system_prompt(strict_system_prompt, history)
        retry_options = _build_options(
            session=session,
            modules=tool_modules,
            system_prompt=retry_composed_system,
            state=retry_state,
            disable_tools=True,
        )
        retry_client = orch._client_factory(retry_options)
        async with retry_client:
            await retry_client.query(user_message)
            async for msg in retry_client.receive_response():
                async for _ev in _events_from_sdk_message(msg, retry_state):
                    pass
        await record_call(
            session,
            surface="chat_orchestrator_retry",
            transport="sdk",
            stats=LLMCallStats(
                model=retry_state.model or DEFAULT_MODEL,
                prompt_tokens=retry_state.prompt_tokens,
                completion_tokens=retry_state.completion_tokens,
                cost_cents=retry_state.cost_cents_total,
            ),
            ctx=log_ctx,
        )
        state.prompt_tokens += retry_state.prompt_tokens
        state.completion_tokens += retry_state.completion_tokens
        state.cost_cents_total += retry_state.cost_cents_total
        state.finish_reason = retry_state.finish_reason
        retry_text = (
            retry_state.final_text
            or "".join(retry_state.fallback_text_parts)
        )
        retry_parsed = parse_citations(retry_text, valid_ids)
        retry_uncited = find_uncited_numerics(retry_parsed.text, retry_parsed.spans)
        if retry_uncited:
            warning_code = "uncited_numeric"
        parsed = retry_parsed

    final_text = parsed.text
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

    suggestions = followups_mod.generate(
        final_text=final_text, tool_names=state.hooks.tool_names
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
        llm_provider="anthropic",
        llm_model=state.model or DEFAULT_MODEL,
        prompt_tokens=state.prompt_tokens,
        completion_tokens=state.completion_tokens,
        cost_cents=Decimal(str(round(state.cost_cents_total, 4))),
        finish_reason=state.finish_reason,
        warning=warning_code,
        suggested_followups=suggestions,
    )
    session.add(assistant_turn)
    await session.flush()
    for ec_id in dict.fromkeys(state.hooks.engine_call_ids):
        session.add(ChatEngineCall(turn_id=assistant_turn.id, engine_call_id=ec_id))
    thread.updated_at = datetime.now(UTC)

    if assistant_idx <= 2 and thread_title_mod.looks_like_raw_user_message(
        thread.title, user_message
    ):
        title_result = await thread_title_mod.generate_title(
            user_message=user_message, assistant_text=final_text
        )
        if title_result.response is not None:
            await record_call(
                session,
                surface="thread_title",
                transport="messages_api",
                stats=LLMCallStats(
                    model=title_result.response.model,
                    prompt_tokens=title_result.response.prompt_tokens,
                    completion_tokens=title_result.response.completion_tokens,
                    cost_cents=title_result.response.cost_cents,
                ),
                ctx=log_ctx,
            )
        if title_result.title:
            thread.title = title_result.title

    await session.commit()

    yield CompletionEvent(
        type="done",
        payload={
            "turn_id": str(assistant_turn.id),
            "thread_id": str(thread_id),
            "finish_reason": state.finish_reason,
            "prompt_tokens": state.prompt_tokens,
            "completion_tokens": state.completion_tokens,
            "cost_cents": round(state.cost_cents_total, 4),
            "model": state.model or DEFAULT_MODEL,
            "provider": "anthropic",
            "engine_call_ids": list(dict.fromkeys(state.hooks.engine_call_ids)),
            "suggested_followups": suggestions,
        },
    )


# ---------------------------------------------------------------------- SDK glue


def _build_options(
    *,
    session: AsyncSession,
    modules: list[str],
    system_prompt: str,
    state: _TurnState,
    disable_tools: bool = False,
) -> ClaudeAgentOptions:
    mcp_server = build_engine_mcp_server(session=session, modules=modules)
    allowed = [] if disable_tools else allowed_tool_names(modules)
    return ClaudeAgentOptions(
        system_prompt=system_prompt,
        mcp_servers={"engine": mcp_server},
        allowed_tools=allowed,
        max_turns=MAX_TOOL_CALLS,
        permission_mode="bypassPermissions",
        hooks={
            "PostToolUse": [
                HookMatcher(hooks=[make_post_tool_use_hook(state.hooks)]),
            ],
        },
    )


def _default_client_factory(options: ClaudeAgentOptions) -> ClaudeSDKClient:
    return ClaudeSDKClient(options=options)


async def _events_from_sdk_message(
    msg: SDKMessage,
    state: _TurnState,
) -> AsyncGenerator[CompletionEvent, None]:
    if isinstance(msg, AssistantMessage):
        if msg.model:
            state.model = msg.model
        for block in msg.content:
            if isinstance(block, TextBlock):
                if block.text:
                    state.fallback_text_parts.append(block.text)
                    yield CompletionEvent(
                        type="text_delta", payload={"text": block.text}
                    )
            elif isinstance(block, ToolUseBlock):
                yield CompletionEvent(
                    type="tool_call",
                    payload={
                        "id": block.id,
                        "name": strip_mcp_prefix(block.name),
                        "arguments": block.input,
                    },
                )
    elif isinstance(msg, UserMessage):
        for tool_use_id in _iter_user_tool_result_ids(msg):
            payload: dict[str, object] = {"tool_call_id": tool_use_id}
            ec_id = _matching_engine_call_id(state.hooks.engine_call_ids)
            if ec_id is not None:
                payload["engine_call_id"] = ec_id
            yield CompletionEvent(type="tool_result", payload=payload)
    elif isinstance(msg, ResultMessage):
        if msg.stop_reason:
            state.finish_reason = _normalize_stop_reason(msg.stop_reason)
        if msg.result and not state.final_text:
            state.final_text = msg.result
        _accumulate_usage(state, msg)


def _iter_user_tool_result_ids(msg: UserMessage) -> list[str]:
    if not isinstance(msg.content, list):
        return []
    out: list[str] = []
    for b in msg.content:
        if isinstance(b, ToolResultBlock):
            out.append(b.tool_use_id)
    return out


def _matching_engine_call_id(engine_call_ids: list[str]) -> str | None:
    return engine_call_ids[-1] if engine_call_ids else None


def _accumulate_usage(state: _TurnState, msg: ResultMessage) -> None:
    usage = msg.usage or {}
    prompt = _coerce_int(usage.get("input_tokens"))
    completion = _coerce_int(usage.get("output_tokens"))
    if prompt:
        state.prompt_tokens += prompt
    if completion:
        state.completion_tokens += completion
    if msg.total_cost_usd is not None:
        state.cost_cents_total += float(msg.total_cost_usd) * 100.0
    else:
        model = state.model or DEFAULT_MODEL
        state.cost_cents_total += cost_cents(model, prompt, completion)
    _ = PRICING_CENTS_PER_MTOK  # keep pricing table reachable for tests


def _coerce_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def _normalize_stop_reason(raw: str) -> str:
    if raw == "tool_use":
        return "tool_use"
    if raw == "max_tokens":
        return "length"
    if raw in ("end_turn", "stop_sequence"):
        return "stop"
    return raw


def _compose_system_prompt(base: str, history: list[tuple[str, str]]) -> str:
    if not history:
        return base
    lines = ["<conversation_history>"]
    for role, content in history:
        lines.append(f"<{role}>{content}</{role}>")
    lines.append("</conversation_history>")
    return base + "\n\n" + "\n".join(lines)


# ---------------------------------------------------------------------- helpers


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
            "suggested_followups": [],
        },
    )


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
    session: AsyncSession,
    thread_id: UUID,
    *,
    exclude_turn_id: UUID | None,
) -> list[tuple[str, str]]:
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
    out: list[tuple[str, str]] = []
    for row in reversed(rows):
        if exclude_turn_id is not None and row.id == exclude_turn_id:
            continue
        if row.role in ("user", "assistant"):
            out.append((row.role, row.content))
    return out
