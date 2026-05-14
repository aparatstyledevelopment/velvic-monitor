"""Small chat-layer data types shared across the orchestrator, the SSE
streaming adapter, and the engine tool dispatcher.

Lives outside `providers/` because we no longer have a provider abstraction:
the orchestrator drives the Claude Agent SDK directly (ADR 0009) and
single-shot LLM calls go through `anthropic_messages_client`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class CompletionEvent:
    """One event in a streaming completion.

    `type` ∈ {text_delta, tool_call, tool_result, warning, done, error}.
    """

    type: str
    payload: dict[str, Any] = field(default_factory=dict)
