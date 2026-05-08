from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import pytest
from pydantic import BaseModel

from app.chat.providers.base import ToolCall
from app.chat.tools import (
    ToolArgumentError,
    UnknownToolError,
    dispatch,
    tool_specs_for_chat,
)
from app.engine.envelope import EngineResult, SourceRef
from app.engine.registry import _REGISTRY, engine_tool


class _Echo(BaseModel):
    value: str


@pytest.fixture
def stub_tool() -> Any:
    name = "_test_echo"

    @engine_tool(
        name=name,
        module="_test",
        description="echo tool used by dispatcher unit tests",
        returns_model=_Echo,
    )
    async def _echo(*, session: Any, value: str, on: date) -> EngineResult[_Echo]:
        _ = session
        return EngineResult(
            engine_call_id="pending",
            tool_name="pending",
            module="_test",
            params={},
            data=_Echo(value=f"{value}@{on.isoformat()}"),
            sources=[SourceRef(id="src1", kind="test", description="x")],
            computed_at=datetime.now(UTC),
            engine_version="pending",
            latency_ms=0,
        )

    yield _echo
    _REGISTRY.pop(name, None)


class _StubSession:
    """Minimal session that swallows ledger writes used by the decorator."""

    async def get(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def add(self, _row: Any) -> None:
        return None

    async def flush(self) -> None:
        return None


@pytest.mark.asyncio
async def test_dispatch_invokes_tool_and_returns_envelope(stub_tool: Any) -> None:
    _ = stub_tool
    call = ToolCall(
        id="call_1",
        name="_test_echo",
        arguments={"value": "hi", "on": "2026-04-30"},
    )
    result = await dispatch(call, session=_StubSession())  # type: ignore[arg-type]
    assert result.tool_call_id == "call_1"
    assert result.tool_name == "_test_echo"
    assert result.engine_call_id.startswith("ec_")
    assert "hi@2026-04-30" in result.envelope_json


@pytest.mark.asyncio
async def test_dispatch_unknown_tool_raises() -> None:
    call = ToolCall(id="x", name="_does_not_exist", arguments={})
    with pytest.raises(UnknownToolError):
        await dispatch(call, session=_StubSession())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_dispatch_validation_error_raises(stub_tool: Any) -> None:
    _ = stub_tool
    call = ToolCall(
        id="call_2", name="_test_echo", arguments={"value": "ok", "on": "not-a-date"}
    )
    with pytest.raises(ToolArgumentError):
        await dispatch(call, session=_StubSession())  # type: ignore[arg-type]


def test_tool_specs_have_input_schemas(stub_tool: Any) -> None:
    _ = stub_tool
    specs = tool_specs_for_chat(["_test"])
    assert any(s.name == "_test_echo" for s in specs)
    schema = next(s for s in specs if s.name == "_test_echo").input_schema
    assert schema["type"] == "object"
    assert "value" in schema["properties"]
    assert "on" in schema["properties"]
    # `title` keys should be stripped
    assert "title" not in schema


def test_tool_specs_includes_drivers_module() -> None:
    import app.engine  # noqa: F401  ensure drivers tools are registered

    specs = tool_specs_for_chat(["drivers"])
    names = {s.name for s in specs}
    assert "get_price_move" in names
    schema = next(s for s in specs if s.name == "get_price_move").input_schema
    assert schema["type"] == "object"
    assert "company_id" in schema["properties"]
    assert "as_of" in schema["properties"]
