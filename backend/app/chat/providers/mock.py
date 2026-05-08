"""Mock LLM provider for tests and local development.

Three ways to use it:
1. `text=` for a fixed text response.
2. `responder=` for a callable that returns either a text str OR a
   CompletionResult (the orchestrator tests use the latter to drive the
   tool loop deterministically).
3. `script=` for a list of CompletionResults consumed in order, simulating
   a multi-turn loop.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable

from app.chat.providers.base import (
    CompletionEvent,
    CompletionResult,
    LLMProvider,
    Message,
    ToolCall,
    ToolSpec,
)

Responder = Callable[
    [str, list[Message], list[ToolSpec] | None],
    str | CompletionResult,
]


class MockProvider(LLMProvider):
    name = "mock"

    def __init__(
        self,
        *,
        text: str | None = None,
        responder: Responder | None = None,
        script: list[CompletionResult] | None = None,
        model: str = "mock-1",
    ) -> None:
        provided = sum(x is not None for x in (text, responder, script))
        if provided != 1:
            raise ValueError("provide exactly one of text=, responder=, or script=")
        self._text = text
        self._responder = responder
        self._script = list(script) if script is not None else None
        self._model = model

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
        if self._script is not None:
            if not self._script:
                raise RuntimeError("MockProvider script exhausted")
            return self._script.pop(0)
        if self._text is not None:
            text = self._text
            return CompletionResult(
                text=text,
                tool_calls=[],
                prompt_tokens=len(system) + sum(len(m.content) for m in messages),
                completion_tokens=len(text),
                cost_cents=0.0,
                model=model or self._model,
                provider=self.name,
                finish_reason="stop",
            )
        assert self._responder is not None
        produced = self._responder(system, messages, tools)
        if isinstance(produced, CompletionResult):
            return produced
        return CompletionResult(
            text=produced,
            tool_calls=[],
            prompt_tokens=len(system) + sum(len(m.content) for m in messages),
            completion_tokens=len(produced),
            cost_cents=0.0,
            model=model or self._model,
            provider=self.name,
            finish_reason="stop",
        )

    async def stream_complete(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        model: str | None = None,
    ) -> AsyncIterator[CompletionEvent]:
        result = await self.complete(
            system=system,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
            model=model,
        )
        if result.text:
            yield CompletionEvent(type="text_delta", payload={"text": result.text})
        for tc in result.tool_calls:
            yield CompletionEvent(
                type="tool_call",
                payload={"id": tc.id, "name": tc.name, "arguments": tc.arguments},
            )
        yield CompletionEvent(
            type="done",
            payload={
                "finish_reason": result.finish_reason,
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "cost_cents": result.cost_cents,
                "model": result.model,
                "provider": result.provider,
                "tool_calls": [
                    {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                    for tc in result.tool_calls
                ],
            },
        )


def make_tool_call_result(
    *,
    tool_name: str,
    arguments: dict[str, object],
    tool_call_id: str = "call_mock",
    text: str = "",
    model: str = "mock-1",
) -> CompletionResult:
    """Helper for building a CompletionResult that asks for a tool call."""
    return CompletionResult(
        text=text,
        tool_calls=[
            ToolCall(id=tool_call_id, name=tool_name, arguments=dict(arguments))
        ],
        prompt_tokens=0,
        completion_tokens=0,
        cost_cents=0.0,
        model=model,
        provider="mock",
        finish_reason="tool_use",
    )
