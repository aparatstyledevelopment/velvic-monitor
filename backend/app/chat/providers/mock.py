"""Mock LLM provider for tests and local development.

Two ways to use it:
1. Inject a callable `responder(system, messages, tools)` returning text.
2. Provide a fixed `text` for trivial cases.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable

from app.chat.providers.base import (
    CompletionEvent,
    CompletionResult,
    LLMProvider,
    Message,
    ToolSpec,
)


class MockProvider(LLMProvider):
    name = "mock"

    def __init__(
        self,
        *,
        text: str | None = None,
        responder: (
            Callable[[str, list[Message], list[ToolSpec] | None], str] | None
        ) = None,
        model: str = "mock-1",
    ) -> None:
        if (text is None) == (responder is None):
            raise ValueError("provide exactly one of text= or responder=")
        self._text = text
        self._responder = responder
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
        text = self._text if self._text is not None else self._responder(system, messages, tools)  # type: ignore[misc]
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
        ev = CompletionEvent()
        ev.type = "text_delta"
        ev.payload = result.text
        yield ev
        done = CompletionEvent()
        done.type = "done"
        done.payload = {"finish_reason": "stop"}
        yield done
