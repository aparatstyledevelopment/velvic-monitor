"""In-process MCP server that exposes the engine tool registry to the
Claude Agent SDK.

Built fresh per chat turn so each tool handler can close over the
request's AsyncSession — that keeps the existing engine tool signature
(`session: AsyncSession, **params`) intact and avoids any contextvars
machinery.

Engine tools remain the source of truth: this module is a thin adapter
between SDK `@tool` handlers and `chat.tools.dispatch()`, which already
does Pydantic coercion + ledger writes.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from claude_agent_sdk import SdkMcpTool, create_sdk_mcp_server, tool
from claude_agent_sdk.types import McpSdkServerConfig
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.tools import (
    ToolArgumentError,
    UnknownToolError,
    _build_input_schema,
    dispatch,
)
from app.chat.types import ToolCall
from app.engine import registry as engine_registry

MCP_SERVER_NAME = "engine"


def build_engine_mcp_server(
    *,
    session: AsyncSession,
    modules: list[str],
) -> McpSdkServerConfig:
    """Build an in-process MCP server exposing all engine tools in `modules`.

    Each tool handler is an async closure that calls `chat.tools.dispatch`
    with the captured `session`. The handler returns the engine envelope
    JSON as a single text content block; PostToolUse hooks parse this to
    capture `engine_call_id`.
    """
    handlers: list[SdkMcpTool[Any]] = []
    for spec in engine_registry.specs_for_modules(modules):
        handlers.append(_make_handler(spec_name=spec.name, session=session))
    return create_sdk_mcp_server(name=MCP_SERVER_NAME, tools=handlers)


def allowed_tool_names(modules: list[str]) -> list[str]:
    """Names the SDK uses to allowlist tools coming from this MCP server."""
    return [
        f"mcp__{MCP_SERVER_NAME}__{spec.name}"
        for spec in engine_registry.specs_for_modules(modules)
    ]


def strip_mcp_prefix(name: str) -> str:
    """Strip `mcp__<server>__` from a tool-use block name."""
    prefix = f"mcp__{MCP_SERVER_NAME}__"
    return name[len(prefix) :] if name.startswith(prefix) else name


def _make_handler(*, spec_name: str, session: AsyncSession) -> SdkMcpTool[Any]:
    spec = engine_registry.get(spec_name)
    schema = _build_input_schema(spec)

    @tool(spec.name, spec.description, schema)
    async def handler(args: dict[str, Any]) -> dict[str, Any]:
        call = ToolCall(
            id=f"tu_{uuid4().hex[:8]}",
            name=spec.name,
            arguments=args,
        )
        try:
            result = await dispatch(call, session=session)
        except (UnknownToolError, ToolArgumentError) as e:
            return {
                "content": [{"type": "text", "text": f'{{"error": "{e}"}}'}],
                "isError": True,
            }
        return {
            "content": [{"type": "text", "text": result.envelope_json}],
        }

    return handler
