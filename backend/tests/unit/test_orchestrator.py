"""Orchestrator unit tests.

These exercise the orchestrator state machine with a faked AsyncSession and
a `FakeSDKClient` that scripts a sequence of Claude Agent SDK messages.
PostToolUse hook invocations are simulated so `engine_call_id`s land on
the turn state the way they would in production. End-to-end tests that
hit a real Postgres + Claude CLI live in tests/integration/.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator, AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)
from pydantic import BaseModel

from app.chat.models import ChatEngineCall, ChatThread, ChatTurn
from app.chat.orchestrator import ChatOrchestrator
from app.chat.topic_gate import TopicDecision
from app.chat.types import CompletionEvent
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
    return {
        "org_id": uuid4(),
        "user_id": uuid4(),
        "thread_id": uuid4(),
        "company_id": 42,
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
    def __init__(self, id: int, name: str, ticker: str = "VOLV-B") -> None:
        self.id = id
        self.name = name
        self.ticker = ticker


class _FakeAccess:
    pass


class _FakeSession:
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
            _FakeCompany: {},
            EngineCall: {},
        },
        scalar_results=[
            _FakeAccess(),  # OrgCompanyAccess lookup
            0,  # next_idx for user turn
            0,  # next_idx for assistant turn
        ],
        execute_results=[[]],
    )


def _patch_session_lookups(
    session: _FakeSession,
    *,
    company: _FakeCompany,
    org: _FakeOrg,
) -> None:
    from app.auth.models import Company, Org  # noqa: PLC0415

    session._get[Company] = {company.id: company}
    session._get[Org] = {org.id: org}


# -------------------------------------------------------------------- FakeSDKClient


@dataclass
class _ScriptedToolCall:
    """One scripted assistant message that wants to call a tool."""

    tool_use_id: str
    tool_name: str  # bare name; orchestrator strips the mcp__engine__ prefix
    arguments: dict[str, Any] = field(default_factory=dict)
    text: str = ""
    envelope: dict[str, Any] = field(default_factory=dict)


@dataclass
class _ScriptedFinal:
    """A final assistant message + result usage."""

    text: str
    model: str = "claude-haiku-4-5-20251001"
    prompt_tokens: int = 10
    completion_tokens: int = 5


class _FakeSDKClient:
    """Stand-in for `claude_agent_sdk.ClaudeSDKClient`.

    The script is a list of `_ScriptedToolCall | _ScriptedFinal`. For each
    tool call, the fake invokes the PostToolUse hook with the configured
    envelope so the orchestrator's hook captures the engine_call_id; then
    it yields the AssistantMessage(ToolUseBlock) and a UserMessage with
    a ToolResultBlock. The final entry yields AssistantMessage(TextBlock)
    + ResultMessage.
    """

    def __init__(
        self,
        options: ClaudeAgentOptions,
        script: list[_ScriptedToolCall | _ScriptedFinal],
    ) -> None:
        self.options = options
        self._script = list(script)
        self.queries: list[str] = []

    async def __aenter__(self) -> "_FakeSDKClient":
        return self

    async def __aexit__(self, *_a: Any) -> bool:
        return False

    async def query(self, prompt: str, session_id: str = "default") -> None:
        _ = session_id
        self.queries.append(prompt)

    async def receive_response(self) -> AsyncIterator[Any]:
        for step in self._script:
            if isinstance(step, _ScriptedToolCall):
                await self._fire_post_tool_use_hook(step)
                yield AssistantMessage(
                    content=[
                        ToolUseBlock(
                            id=step.tool_use_id,
                            name=f"mcp__engine__{step.tool_name}",
                            input=step.arguments,
                        )
                    ],
                    model="claude-haiku-4-5-20251001",
                    parent_tool_use_id=None,
                    error=None,
                    usage=None,
                    message_id=None,
                    stop_reason=None,
                    session_id=None,
                    uuid=None,
                )
                yield UserMessage(
                    content=[
                        ToolResultBlock(
                            tool_use_id=step.tool_use_id,
                            content=json.dumps(step.envelope),
                            is_error=None,
                        )
                    ],
                    uuid=None,
                    parent_tool_use_id=None,
                    tool_use_result=None,
                )
            else:
                yield AssistantMessage(
                    content=[TextBlock(text=step.text)],
                    model=step.model,
                    parent_tool_use_id=None,
                    error=None,
                    usage=None,
                    message_id=None,
                    stop_reason="end_turn",
                    session_id=None,
                    uuid=None,
                )
                yield ResultMessage(
                    subtype="success",
                    duration_ms=10,
                    duration_api_ms=8,
                    is_error=False,
                    num_turns=1,
                    session_id="test",
                    stop_reason="end_turn",
                    total_cost_usd=0.001,
                    usage={
                        "input_tokens": step.prompt_tokens,
                        "output_tokens": step.completion_tokens,
                    },
                    result=step.text,
                    structured_output=None,
                    model_usage=None,
                    permission_denials=None,
                    deferred_tool_use=None,
                    errors=None,
                    api_error_status=None,
                    uuid=None,
                )

    async def _fire_post_tool_use_hook(self, step: _ScriptedToolCall) -> None:
        hooks = self.options.hooks or {}
        matchers = hooks.get("PostToolUse", [])
        for matcher in matchers:
            for cb in matcher.hooks:
                await cb(
                    {
                        "session_id": "test",
                        "transcript_path": "/tmp/x",
                        "cwd": "/tmp",
                        "agent_id": "test",
                        "agent_type": "test",
                        "hook_event_name": "PostToolUse",
                        "tool_name": f"mcp__engine__{step.tool_name}",
                        "tool_input": step.arguments,
                        "tool_response": {
                            "content": [
                                {"type": "text", "text": json.dumps(step.envelope)}
                            ]
                        },
                        "tool_use_id": step.tool_use_id,
                    },
                    step.tool_use_id,
                    {"signal": None},
                )


def _orchestrator_with_client(
    script: list[_ScriptedToolCall | _ScriptedFinal],
    *,
    on_topic: bool = True,
    reason: str = "",
) -> ChatOrchestrator:
    async def fake_classify(_message: str, model: str | None = None) -> TopicDecision:
        _ = model
        return TopicDecision(on_topic=on_topic, reason=reason)

    scripts: list[list[_ScriptedToolCall | _ScriptedFinal]] = [list(script)]

    def client_factory(options: ClaudeAgentOptions) -> _FakeSDKClient:
        next_script = scripts.pop(0) if scripts else []
        return _FakeSDKClient(options, next_script)

    return ChatOrchestrator(
        client_factory=client_factory,  # type: ignore[arg-type]
        gate_classify_fn=fake_classify,
        tool_modules=("_test",),
    )


def _orchestrator_with_two_scripts(
    first: list[_ScriptedToolCall | _ScriptedFinal],
    second: list[_ScriptedToolCall | _ScriptedFinal],
) -> ChatOrchestrator:
    async def fake_classify(_message: str, model: str | None = None) -> TopicDecision:
        _ = model
        return TopicDecision(on_topic=True, reason="")

    scripts: list[list[_ScriptedToolCall | _ScriptedFinal]] = [list(first), list(second)]

    def client_factory(options: ClaudeAgentOptions) -> _FakeSDKClient:
        next_script = scripts.pop(0) if scripts else []
        return _FakeSDKClient(options, next_script)

    return ChatOrchestrator(
        client_factory=client_factory,  # type: ignore[arg-type]
        gate_classify_fn=fake_classify,
        tool_modules=("_test",),
    )


async def _collect(it: AsyncGenerator[CompletionEvent, None]) -> list[CompletionEvent]:
    out: list[CompletionEvent] = []
    async for ev in it:
        out.append(ev)
    return out


# -------------------------------------------------------------------- tests


@pytest.mark.asyncio
async def test_off_topic_emits_refusal_without_calling_sdk(
    fixtures: dict[str, Any],
) -> None:
    session = _build_session(fixtures)
    company = _FakeCompany(fixtures["company_id"], "Volvo Group")
    org = _FakeOrg(fixtures["org_id"])
    _patch_session_lookups(session, company=company, org=org)
    user = _FakeUser(fixtures["user_id"], fixtures["org_id"])

    sdk_calls: list[int] = []

    def client_factory(_options: ClaudeAgentOptions) -> _FakeSDKClient:
        sdk_calls.append(1)
        raise AssertionError("SDK client should not be constructed on off-topic")

    async def fake_classify(_msg: str, model: str | None = None) -> TopicDecision:
        _ = model
        return TopicDecision(on_topic=False, reason="not a Swedish-listed name")

    orch = ChatOrchestrator(
        client_factory=client_factory,  # type: ignore[arg-type]
        gate_classify_fn=fake_classify,
        tool_modules=("_test",),
    )

    it = await orch.process_turn(
        thread_id=fixtures["thread_id"],
        user_message="recommend Tesla stock",
        session=session,  # type: ignore[arg-type]
        user=user,  # type: ignore[arg-type]
    )
    events = await _collect(it)

    assert sdk_calls == []
    types = [e.type for e in events]
    assert types[0] == "text_delta"
    assert "Volvo Group" in events[0].payload["text"]
    assert types[-1] == "done"
    assert events[-1].payload["finish_reason"] == "refusal"
    assert sum(1 for o in session.added if isinstance(o, ChatTurn)) == 2


@pytest.mark.asyncio
async def test_bypass_topic_gate_skips_classifier_and_runs_main_provider(
    fixtures: dict[str, Any],
) -> None:
    """Demo escape hatch: bypass_topic_gate=True must skip the classifier
    entirely (no gate provider call) and let the model answer even
    obviously-off-topic prompts."""
    session = _build_session(fixtures)
    company = _FakeCompany(fixtures["company_id"], "Volvo Group")
    org = _FakeOrg(fixtures["org_id"])
    _patch_session_lookups(session, company=company, org=org)
    user = _FakeUser(fixtures["user_id"], fixtures["org_id"])

    gate_calls: list[int] = []

    async def boom_classify(_msg: str, model: str | None = None) -> TopicDecision:
        _ = model
        gate_calls.append(1)
        raise AssertionError("gate classifier must not be called when bypass=True")

    script: list[_ScriptedToolCall | _ScriptedFinal] = [
        _ScriptedFinal(text="Hello, here's a generic answer."),
    ]
    scripts: list[list[_ScriptedToolCall | _ScriptedFinal]] = [script]

    def client_factory(options: ClaudeAgentOptions) -> _FakeSDKClient:
        return _FakeSDKClient(options, scripts.pop(0) if scripts else [])

    orch = ChatOrchestrator(
        client_factory=client_factory,  # type: ignore[arg-type]
        gate_classify_fn=boom_classify,
        tool_modules=("_test",),
    )

    it = await orch.process_turn(
        thread_id=fixtures["thread_id"],
        user_message="recommend Tesla stock",
        session=session,  # type: ignore[arg-type]
        user=user,  # type: ignore[arg-type]
        bypass_topic_gate=True,
    )
    events = await _collect(it)

    assert gate_calls == []
    types = [e.type for e in events]
    assert types[-1] == "done"
    assert events[-1].payload["finish_reason"] != "refusal"


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

    ec_id = "ec_abc123"
    script: list[_ScriptedToolCall | _ScriptedFinal] = [
        _ScriptedToolCall(
            tool_use_id="tu_1",
            tool_name="_orch_echo",
            arguments={"value": "hi"},
            envelope={"engine_call_id": ec_id, "data": {"value": "hi"}, "sources": []},
        ),
        _ScriptedFinal(text=f"The answer is 42 [{ec_id}]."),
    ]
    orch = _orchestrator_with_client(script)

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
    text_events = [e for e in events if e.type == "text_delta"]
    final_text = text_events[-1].payload["text"]
    assert "42" in final_text
    assert ec_id in final_text or final_text.startswith("The answer is 42")

    done = events[-1]
    assert done.type == "done"
    assert ec_id in done.payload["engine_call_ids"]
    assert done.payload["finish_reason"] == "stop"

    chat_turns = [o for o in session.added if isinstance(o, ChatTurn)]
    chat_links = [o for o in session.added if isinstance(o, ChatEngineCall)]
    assert len(chat_turns) == 2
    assert len(chat_links) == 1


@pytest.mark.asyncio
async def test_uncited_numeric_triggers_strict_retry_and_warning(
    fixtures: dict[str, Any],
) -> None:
    session = _build_session(fixtures)
    company = _FakeCompany(fixtures["company_id"], "Volvo Group")
    org = _FakeOrg(fixtures["org_id"])
    _patch_session_lookups(session, company=company, org=org)
    user = _FakeUser(fixtures["user_id"], fixtures["org_id"])

    bad: list[_ScriptedToolCall | _ScriptedFinal] = [
        _ScriptedFinal(text="The stock fell 2.1 percent yesterday."),
    ]
    retry_bad: list[_ScriptedToolCall | _ScriptedFinal] = [
        _ScriptedFinal(text="The stock fell 2.1 percent yesterday."),
    ]
    orch = _orchestrator_with_two_scripts(bad, retry_bad)

    it = await orch.process_turn(
        thread_id=fixtures["thread_id"],
        user_message="how did volvo move?",
        session=session,  # type: ignore[arg-type]
        user=user,  # type: ignore[arg-type]
    )
    events = await _collect(it)

    warnings = [e for e in events if e.type == "warning"]
    assert len(warnings) == 1
    assert warnings[0].payload["code"] == "uncited_numeric"
    assert events[-1].type == "done"


def test_options_carry_max_turns_cap() -> None:
    """The orchestrator must thread MAX_TOOL_CALLS through ClaudeAgentOptions.max_turns."""
    import app.engine  # noqa: F401  registers the drivers tools

    from app.chat.orchestrator import MAX_TOOL_CALLS, _TurnState, _build_options
    from app.chat.sdk_hooks import TurnHookState

    state = _TurnState(hooks=TurnHookState())
    options = _build_options(
        session=None,  # type: ignore[arg-type]
        modules=["drivers"],
        system_prompt="x",
        state=state,
    )
    assert options.max_turns == MAX_TOOL_CALLS
    assert options.allowed_tools  # drivers module has tools registered
    assert all(n.startswith("mcp__engine__") for n in options.allowed_tools)

    options_strict = _build_options(
        session=None,  # type: ignore[arg-type]
        modules=["drivers"],
        system_prompt="x",
        state=state,
        disable_tools=True,
    )
    assert options_strict.allowed_tools == []
