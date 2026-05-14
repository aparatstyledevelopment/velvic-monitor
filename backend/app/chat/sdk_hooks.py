"""SDK hooks that wire Engine/Narrator discipline into the agent loop.

`PostToolUse` fires after every engine tool the model calls; it parses the
returned envelope and records the `engine_call_id` on the turn state.
That list is what citation parsing later validates against in the
orchestrator.

There is no `Stop` hook: `StopHookInput` doesn't expose the assistant's
final text, so the orchestrator does the citation pass itself once the
SDK message stream ends. The strict-prompt retry path is owned by the
orchestrator as well.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk import HookContext
from claude_agent_sdk.types import HookInput, HookJSONOutput

from app.chat.sdk_mcp import MCP_SERVER_NAME
from app.core.logging import logger

HookCallback = Callable[
    [HookInput, str | None, HookContext],
    Awaitable[HookJSONOutput],
]


@dataclass
class TurnHookState:
    """Mutable bag the hooks write into and the orchestrator reads after."""

    engine_call_ids: list[str] = field(default_factory=list)
    tool_errors: list[str] = field(default_factory=list)


def make_post_tool_use_hook(state: TurnHookState) -> HookCallback:
    async def hook(
        input_data: HookInput,
        _tool_use_id: str | None,
        _ctx: HookContext,
    ) -> HookJSONOutput:
        data = _as_dict(input_data)
        if not _is_engine_tool(data):
            return {}
        envelope_json = _extract_envelope_text(data)
        if envelope_json is None:
            return {}
        try:
            envelope = json.loads(envelope_json)
        except json.JSONDecodeError:
            logger.warning("post_tool_use_envelope_unparseable")
            return {}
        ec_id = envelope.get("engine_call_id")
        if isinstance(ec_id, str) and ec_id.startswith("ec_"):
            state.engine_call_ids.append(ec_id)
        elif "error" in envelope:
            state.tool_errors.append(str(envelope["error"]))
        return {}

    return hook


def _as_dict(input_data: HookInput) -> dict[str, Any]:
    return dict(input_data) if isinstance(input_data, dict) else {}


def _is_engine_tool(data: dict[str, Any]) -> bool:
    name = data.get("tool_name")
    return isinstance(name, str) and name.startswith(f"mcp__{MCP_SERVER_NAME}__")


def _extract_envelope_text(input_data: dict[str, Any]) -> str | None:
    """Engine MCP handler returns `{"content": [{"type": "text", "text": <json>}]}`.

    The CLI may unwrap this differently — try both shapes defensively.
    """
    resp = input_data.get("tool_response")
    if isinstance(resp, dict):
        content = resp.get("content")
        if isinstance(content, list) and content:
            first = content[0]
            if isinstance(first, dict):
                text = first.get("text")
                if isinstance(text, str):
                    return text
        text = resp.get("text")
        if isinstance(text, str):
            return text
    if isinstance(resp, list) and resp:
        first = resp[0]
        if isinstance(first, dict):
            text = first.get("text")
            if isinstance(text, str):
                return text
    if isinstance(resp, str):
        return resp
    return None
