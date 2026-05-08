"""Provider-agnostic LLM interface.

The orchestrator and briefing composer talk to this interface; they do
not import any provider SDK directly. See ADR 0004.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol


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


@dataclass(frozen=True)
class Message:
    """A conversation message.

    Shapes by role:
    - 'system': content is the system prompt (rarely passed; system goes
       in the dedicated `system` arg). content is plain str.
    - 'user': content is plain str.
    - 'assistant': content is the model's text. If the assistant is making
       tool calls, `tool_calls` is the list and content may be empty.
    - 'tool': content is the JSON-serialised tool result; `tool_call_id`
       points to the assistant's originating ToolCall.id.
    """

    role: str
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None
    tool_name: str | None = None


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


@dataclass
class CompletionEvent:
    """One event in a streaming completion.

    `type` ∈ {text_delta, tool_call, done, error}.

    Payload shapes:
    - text_delta: {"text": str}
    - tool_call:  {"id": str, "name": str, "arguments": dict}
    - done:       {"finish_reason": str, "prompt_tokens": int,
                   "completion_tokens": int, "cost_cents": float,
                   "model": str, "provider": str,
                   "tool_calls": [{"id","name","arguments"}]}
    - error:      {"message": str}
    """

    type: str
    payload: dict[str, Any] = field(default_factory=dict)


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
    ) -> CompletionResult: ...

    def stream_complete(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        model: str | None = None,
    ) -> AsyncIterator[CompletionEvent]: ...
