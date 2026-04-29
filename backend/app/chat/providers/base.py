"""Provider-agnostic LLM interface.

The orchestrator and briefing composer talk to this interface; they do
not import any provider SDK directly. See ADR 0004.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(frozen=True)
class Message:
    role: str  # 'system' | 'user' | 'assistant' | 'tool'
    content: str
    tool_call_id: str | None = None
    tool_name: str | None = None


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class CompletionResult:
    text: str
    tool_calls: list[ToolCall]
    prompt_tokens: int
    completion_tokens: int
    cost_cents: float
    model: str
    provider: str
    finish_reason: str  # 'stop' | 'tool_use' | 'length' | 'error'


class CompletionEvent:
    """Yielded by streaming providers. v1 chat will use this; the
    briefing composer uses non-streaming `complete`."""

    type: str  # 'text_delta' | 'tool_call' | 'tool_result' | 'done' | 'error'
    payload: Any


class LLMProvider(Protocol):
    name: str

    async def complete(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        model: str | None = None,
    ) -> CompletionResult:
        ...

    def stream_complete(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        model: str | None = None,
    ) -> AsyncIterator[CompletionEvent]:
        ...
