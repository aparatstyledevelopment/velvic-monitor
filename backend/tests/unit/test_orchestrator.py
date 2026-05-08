"""Orchestrator unit tests.

These exercise the orchestrator state machine with a faked AsyncSession and
a scripted MockProvider. The fake session implements only the methods the
orchestrator (and the @engine_tool decorator's ledger ops) actually call.
End-to-end tests that hit a real Postgres live in tests/integration/.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel

from app.chat.models import ChatEngineCall, ChatThread, ChatTurn
from app.chat.orchestrator import ChatOrchestrator
from app.chat.providers.base import (
    CompletionEvent,
    CompletionResult,
    LLMProvider,
    Message,
    ToolSpec,
)
from app.chat.providers.mock import MockProvider, make_tool_call_result
from app.engine.envelope import EngineResult, SourceRef
from app.engine.models import EngineCall
from app.engine.registry import _REGISTRY, engine_tool

# -------------------------------------------------------------------- fixtures


class _Echo(BaseModel):
    value: str


@pytest.fixture
def echo_tool() -> Any:
    name = "_orch_echo"

    @engine_tool(
        name=name,
        module="_test",
        description="echo tool used by orchestrator unit tests",
        returns_model=_Echo,
    )
    async def _echo(*, session: Any, value: str) -> EngineResult[_Echo]:
        _ = session
        return EngineResult(
            engine_call_id="pending",
            tool_name="pending",
            module="_test",
            params={},
            data=_Echo(value=value),
            sources=[SourceRef(id="src1", kind="test", description="x")],
            computed_at=datetime.now(UTC),
            engine_version="pending",
            latency_ms=0,
        )

    yield
    _REGISTRY.pop(name, None)


@pytest.fixture
def fixtures() -> dict[str, Any]:
    org_id = uuid4()
    user_id = uuid4()
    thread_id = uuid4()
    company_id = 42
    return {
        "org_id": org_id,
        "user_id": user_id,
        "thread_id": thread_id,
        "company_id": company_id,
    }


class _FakeOrg:
    def __init__(self, id: UUID) -> None:
        self.id = id
        self.llm_provider_pref = "anthropic"


class _FakeUser:
    def __init__(self, id: UUID, org_id: UUID) -> None:
        self.id = id
        self.org_id = org_id


class _FakeCompany:
    def __init__(self, id: int, name: str) -> None:
        self.id = id
        self.name = name


class _FakeAccess:
    pass


class _FakeSession:
    """Just enough AsyncSession surface for the orchestrator + ledger.

    Pre-seeds get() lookups by class. scalar/execute respond from a scripted
    queue keyed on call order, since SQLAlchemy stmts don't have stable
    string keys we could route on.
    """

    def __init__(
        self,
        *,
        seeded_get: dict[type, dict[Any, Any]],
        scalar_results: list[Any],
        execute_results: list[list[Any]],
    ) -> None:
        self._get = seeded_get
        self._scalar_results = list(scalar_results)
        self._execute_results = list(execute_results)
        self.added: list[Any] = []
        self.commits = 0
        self.flushes = 0

    async def get(self, model: type, key: Any) -> Any:
        return self._get.get(model, {}).get(key)

    async def scalar(self, _stmt: Any) -> Any:
        if not self._scalar_results:
            return None
        return self._scalar_results.pop(0)

    async def execute(self, _stmt: Any) -> Any:
        rows = self._execute_results.pop(0) if self._execute_results else []
        return _FakeExecuteResult(rows)

    def add(self, obj: Any) -> None:
        # Mimic Postgres-side default: assign an id on flush if missing.
        self.added.append(obj)

    async def flush(self) -> None:
        self.flushes += 1
        for obj in self.added:
            if hasattr(obj, "id") and getattr(obj, "id", None) is None:
                obj.id = uuid4()

    async def commit(self) -> None:
        self.commits += 1


class _FakeExecuteResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalars(self) -> _FakeScalars:
        return _FakeScalars(self._rows)


class _FakeScalars:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        return list(self._rows)


def _build_session(fixtures: dict[str, Any]) -> _FakeSession:
    thread = ChatThread()
    thread.id = fixtures["thread_id"]
    thread.org_id = fixtures["org_id"]
    thread.user_id = fixtures["user_id"]
    thread.company_id = fixtures["company_id"]
    thread.title = "Why did Volvo move?"
    thread.is_archived = False
    thread.created_at = datetime.now(UTC)
    thread.updated_at = datetime.now(UTC)

    return _FakeSession(
        seeded_get={
            ChatThread: {fixtures["thread_id"]: thread},
            _FakeCompany: {},  # unused
            EngineCall: {},  # unused — fake tool returns no cache hit
        },
        scalar_results=[
            _FakeAccess(),  # OrgCompanyAccess lookup
            0,  # next_idx for user turn
            0,  # next_idx for assistant turn
        ],
        execute_results=[[]],  # empty history
    )


def _patch_session_lookups(
    session: _FakeSession,
    *,
    company: _FakeCompany,
    org: _FakeOrg,
) -> None:
    from app.auth.models import Company, Org  # noqa: PLC0415  (delayed import)

    session._get[Company] = {company.id: company}
    session._get[Org] = {org.id: org}


def _orchestrator_with_provider(provider: LLMProvider) -> ChatOrchestrator:
    return ChatOrchestrator(
        provider_factory=lambda _org: provider,
        gate_provider_factory=lambda _org: MockProvider(text="ON_TOPIC"),
        tool_modules=("_test",),
    )


async def _collect(it: AsyncIterator[CompletionEvent]) -> list[CompletionEvent]:
    out: list[CompletionEvent] = []
    async for ev in it:
        out.append(ev)
    return out


# -------------------------------------------------------------------- tests


@pytest.mark.asyncio
async def test_off_topic_emits_refusal_without_calling_main_provider(
    fixtures: dict[str, Any],
) -> None:
    session = _build_session(fixtures)
    company = _FakeCompany(fixtures["company_id"], "Volvo Group")
    org = _FakeOrg(fixtures["org_id"])
    _patch_session_lookups(session, company=company, org=org)
    user = _FakeUser(fixtures["user_id"], fixtures["org_id"])

    main_calls: list[int] = []

    class _SpyProvider:
        name = "spy"

        async def complete(self, **_kw: Any) -> CompletionResult:
            main_calls.append(1)
            raise AssertionError("main provider should not be called on off-topic")

        async def stream_complete(self, **_kw: Any) -> AsyncIterator[CompletionEvent]:
            raise AssertionError("main provider should not be called on off-topic")
            yield  # pragma: no cover

    orch = ChatOrchestrator(
        provider_factory=lambda _o: _SpyProvider(),  # type: ignore[arg-type, return-value]
        gate_provider_factory=lambda _o: MockProvider(
            text="OFF_TOPIC: not a Swedish-listed name"
        ),
        tool_modules=("_test",),
    )

    it = await orch.process_turn(
        thread_id=fixtures["thread_id"],
        user_message="recommend Tesla stock",
        session=session,  # type: ignore[arg-type]
        user=user,  # type: ignore[arg-type]
    )
    events = await _collect(it)

    assert main_calls == []
    types = [e.type for e in events]
    assert types[0] == "text_delta"
    assert "Volvo Group" in events[0].payload["text"]
    assert types[-1] == "done"
    assert events[-1].payload["finish_reason"] == "refusal"
    # User turn + assistant refusal turn persisted.
    assert sum(1 for o in session.added if isinstance(o, ChatTurn)) == 2


@pytest.mark.asyncio
async def test_tool_loop_dispatches_then_emits_final_with_citations(
    fixtures: dict[str, Any], echo_tool: Any
) -> None:
    _ = echo_tool
    session = _build_session(fixtures)
    company = _FakeCompany(fixtures["company_id"], "Volvo Group")
    org = _FakeOrg(fixtures["org_id"])
    _patch_session_lookups(session, company=company, org=org)
    user = _FakeUser(fixtures["user_id"], fixtures["org_id"])

    # Provider script: round 1 → tool_use, round 2 → final text with citation.
    script = [
        make_tool_call_result(
            tool_name="_orch_echo",
            arguments={"value": "hi"},
            tool_call_id="tu_1",
            text="checking...",
        ),
    ]

    captured_engine_call_id: dict[str, str] = {}

    def final_responder(
        system: str, messages: list[Message], _tools: list[ToolSpec] | None
    ) -> str | CompletionResult:
        # Pull engine_call_id from the most-recent tool message.
        for m in reversed(messages):
            if m.role == "tool":
                import json as _json

                env = _json.loads(m.content)
                captured_engine_call_id["id"] = env["engine_call_id"]
                ec = env["engine_call_id"]
                return f"The answer is 42 [{ec}]."
        return "no tool result found"

    provider = MockProvider(
        responder=lambda s, msgs, tools: (
            script.pop(0) if script else final_responder(s, msgs, tools)
        )
    )
    orch = _orchestrator_with_provider(provider)

    it = await orch.process_turn(
        thread_id=fixtures["thread_id"],
        user_message="why did volvo move?",
        session=session,  # type: ignore[arg-type]
        user=user,  # type: ignore[arg-type]
    )
    events = await _collect(it)

    types = [e.type for e in events]
    assert "tool_call" in types
    assert "tool_result" in types
    final_text_events = [e for e in events if e.type == "text_delta"]
    final_text = final_text_events[-1].payload["text"]
    assert "42" in final_text
    assert captured_engine_call_id["id"] in final_text or final_text.startswith(
        "The answer is 42"
    )

    done = events[-1]
    assert done.type == "done"
    assert done.payload["engine_call_ids"]
    assert done.payload["finish_reason"] in ("stop", "tool_use")

    # Persistence: user turn + assistant turn + 1 engine-call link
    chat_turns = [o for o in session.added if isinstance(o, ChatTurn)]
    chat_links = [o for o in session.added if isinstance(o, ChatEngineCall)]
    assert len(chat_turns) == 2
    assert len(chat_links) == 1


@pytest.mark.asyncio
async def test_uncited_numeric_triggers_strict_retry_and_warning(
    fixtures: dict[str, Any]
) -> None:
    session = _build_session(fixtures)
    company = _FakeCompany(fixtures["company_id"], "Volvo Group")
    org = _FakeOrg(fixtures["org_id"])
    _patch_session_lookups(session, company=company, org=org)
    user = _FakeUser(fixtures["user_id"], fixtures["org_id"])

    # Round 1 returns text with a numeric and NO citation. Round 2 (strict)
    # also fails to cite — we expect a `warning` event to be emitted.
    script = [
        CompletionResult(
            text="The stock fell 2.1 percent yesterday.",
            tool_calls=[],
            prompt_tokens=10,
            completion_tokens=8,
            cost_cents=0.001,
            model="mock-1",
            provider="mock",
            finish_reason="stop",
        ),
        CompletionResult(
            text="The stock fell 2.1 percent yesterday.",
            tool_calls=[],
            prompt_tokens=10,
            completion_tokens=8,
            cost_cents=0.001,
            model="mock-1",
            provider="mock",
            finish_reason="stop",
        ),
    ]
    provider = MockProvider(script=script)
    orch = _orchestrator_with_provider(provider)

    it = await orch.process_turn(
        thread_id=fixtures["thread_id"],
        user_message="how did volvo move?",
        session=session,  # type: ignore[arg-type]
        user=user,  # type: ignore[arg-type]
    )
    events = await _collect(it)

    warning_events = [e for e in events if e.type == "warning"]
    assert len(warning_events) == 1
    assert warning_events[0].payload["code"] == "uncited_numeric"
    assert events[-1].type == "done"


@pytest.mark.asyncio
async def test_tool_call_cap_forces_final_answer(
    fixtures: dict[str, Any], echo_tool: Any
) -> None:
    _ = echo_tool
    session = _build_session(fixtures)
    company = _FakeCompany(fixtures["company_id"], "Volvo Group")
    org = _FakeOrg(fixtures["org_id"])
    _patch_session_lookups(session, company=company, org=org)
    user = _FakeUser(fixtures["user_id"], fixtures["org_id"])

    # Build 8 tool-call rounds + a final text round.
    script: list[CompletionResult] = [
        make_tool_call_result(
            tool_name="_orch_echo",
            arguments={"value": f"v{i}"},
            tool_call_id=f"tu_{i}",
        )
        for i in range(8)
    ]
    script.append(
        CompletionResult(
            text="ok done.",
            tool_calls=[],
            prompt_tokens=1,
            completion_tokens=1,
            cost_cents=0.0,
            model="mock-1",
            provider="mock",
            finish_reason="stop",
        )
    )
    captured_tools_arg: list[Iterable[ToolSpec] | None] = []

    def responder(
        system: str, messages: list[Message], tools: list[ToolSpec] | None
    ) -> CompletionResult:
        captured_tools_arg.append(tools)
        return script.pop(0)

    provider = MockProvider(responder=responder)
    orch = _orchestrator_with_provider(provider)

    it = await orch.process_turn(
        thread_id=fixtures["thread_id"],
        user_message="run a lot of tools",
        session=session,  # type: ignore[arg-type]
        user=user,  # type: ignore[arg-type]
    )
    events = await _collect(it)

    # 8 tool dispatches + final text.
    tool_call_events = [e for e in events if e.type == "tool_call"]
    assert len(tool_call_events) == 8

    # Last call to provider should have tools=None (cap reached).
    assert captured_tools_arg[-1] is None
    # Earlier calls had tools.
    assert captured_tools_arg[0] is not None

    assert events[-1].type == "done"
    assert events[-1].payload["finish_reason"] in ("stop", "tool_use")
