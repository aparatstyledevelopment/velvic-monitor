"""Anthropic Messages API provider.

Phase-1 surface: non-streaming `complete()` for the briefing composer
and the news-summary tool. Streaming used by the chat orchestrator
arrives in Phase 2 alongside provider-specific tool-call mapping.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.chat.providers.base import (
    CompletionEvent,
    CompletionResult,
    LLMProvider,
    Message,
    ToolSpec,
)
from app.core.config import get_settings


DEFAULT_MODEL = "claude-haiku-4-5-20251001"
PRICING_CENTS_PER_MTOK = {
    # USD per million tokens, converted to cents (placeholder; refresh
    # against the live price card before billing real customers).
    "claude-haiku-4-5-20251001": {"prompt": 100.0, "completion": 500.0},
    "claude-sonnet-4-6": {"prompt": 300.0, "completion": 1500.0},
    "claude-opus-4-7": {"prompt": 1500.0, "completion": 7500.0},
}


class AnthropicProvider(LLMProvider):
    name = "anthropic"
    base_url = "https://api.anthropic.com/v1/messages"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._http = http_client

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
        api_key = self._api_key or get_settings().anthropic_api_key
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not configured")
        chosen_model = model or DEFAULT_MODEL
        body: dict[str, Any] = {
            "model": chosen_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": [
                {"role": _role(m.role), "content": m.content}
                for m in messages
                if m.role in ("user", "assistant")
            ],
        }
        if tools:
            body["tools"] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.input_schema,
                }
                for t in tools
            ]

        async with self._http_ctx() as client:
            resp = await client.post(
                self.base_url,
                json=body,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")
        usage = data.get("usage", {})
        prompt_tokens = int(usage.get("input_tokens", 0))
        completion_tokens = int(usage.get("output_tokens", 0))
        return CompletionResult(
            text=text,
            tool_calls=[],
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_cents=_cost_cents(chosen_model, prompt_tokens, completion_tokens),
            model=chosen_model,
            provider=self.name,
            finish_reason=data.get("stop_reason") or "stop",
        )

    async def stream_complete(  # type: ignore[override]
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        model: str | None = None,
    ) -> AsyncIterator[CompletionEvent]:
        # Phase-2 will implement true SSE streaming; for now, emit one delta.
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
        done.payload = {"finish_reason": result.finish_reason}
        yield done

    def _http_ctx(self) -> httpx.AsyncClient:
        if self._http is not None:
            return _NoCloseClient(self._http)
        return httpx.AsyncClient(timeout=httpx.Timeout(60.0))


class _NoCloseClient:
    """Thin wrapper so we can yield an injected client without closing it."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def __aenter__(self) -> httpx.AsyncClient:
        return self._client

    async def __aexit__(self, *_: Any) -> None:
        return None


def _role(r: str) -> str:
    return "user" if r == "user" else "assistant"


def _cost_cents(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    p = PRICING_CENTS_PER_MTOK.get(model, {"prompt": 100.0, "completion": 500.0})
    return (prompt_tokens / 1_000_000) * p["prompt"] + (completion_tokens / 1_000_000) * p["completion"]
