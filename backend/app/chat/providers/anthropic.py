"""Anthropic Messages API provider.

Implements the LLMProvider protocol with:
- non-streaming `complete()` (used by the briefing composer + topic gate),
- streaming `stream_complete()` mapping Anthropic SSE events to our
  CompletionEvent shape, including tool-use input_json_delta accumulation,
- tool-use block parsing in both paths so the orchestrator gets ToolCalls.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.chat.providers.base import (
    CompletionEvent,
    CompletionResult,
    LLMProvider,
    Message,
    ToolCall,
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
        api_key = self._resolve_api_key()
        chosen_model = model or DEFAULT_MODEL
        body = self._build_request_body(
            system=system,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
            model=chosen_model,
            stream=False,
        )

        if self._http is not None:
            data = await self._post_json(self._http, body, api_key)
        else:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                data = await self._post_json(client, body, api_key)

        text, tool_calls = _parse_content_blocks(data.get("content", []))
        usage = data.get("usage", {})
        prompt_tokens = int(usage.get("input_tokens", 0))
        completion_tokens = int(usage.get("output_tokens", 0))
        return CompletionResult(
            text=text,
            tool_calls=tool_calls,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_cents=_cost_cents(chosen_model, prompt_tokens, completion_tokens),
            model=chosen_model,
            provider=self.name,
            finish_reason=_normalize_stop_reason(data.get("stop_reason")),
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
        api_key = self._resolve_api_key()
        chosen_model = model or DEFAULT_MODEL
        body = self._build_request_body(
            system=system,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
            model=chosen_model,
            stream=True,
        )

        if self._http is not None:
            async for ev in self._stream_through(
                self._http, body, api_key, chosen_model
            ):
                yield ev
        else:
            async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
                async for ev in self._stream_through(
                    client, body, api_key, chosen_model
                ):
                    yield ev

    async def _stream_through(
        self,
        client: httpx.AsyncClient,
        body: dict[str, Any],
        api_key: str,
        chosen_model: str,
    ) -> AsyncIterator[CompletionEvent]:
        accumulator = _StreamAccumulator()
        async with client.stream(
            "POST",
            self.base_url,
            json=body,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
                "accept": "text/event-stream",
            },
        ) as resp:
            resp.raise_for_status()
            async for raw_line in resp.aiter_lines():
                if not raw_line or not raw_line.startswith("data:"):
                    continue
                payload = raw_line[len("data:") :].strip()
                if not payload:
                    continue
                try:
                    event = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                async for emitted in accumulator.feed(event):
                    yield emitted

        prompt_tokens, completion_tokens = accumulator.usage
        yield CompletionEvent(
            type="done",
            payload={
                "finish_reason": accumulator.finish_reason or "stop",
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost_cents": _cost_cents(
                    chosen_model, prompt_tokens, completion_tokens
                ),
                "model": chosen_model,
                "provider": self.name,
                "tool_calls": [
                    {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                    for tc in accumulator.tool_calls
                ],
            },
        )

    def _resolve_api_key(self) -> str:
        api_key = self._api_key or get_settings().anthropic_api_key
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not configured")
        return api_key

    def _build_request_body(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[ToolSpec] | None,
        max_tokens: int,
        temperature: float,
        model: str,
        stream: bool,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": [_serialize_message(m) for m in messages],
            "stream": stream,
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
        return body

    async def _post_json(
        self,
        client: httpx.AsyncClient,
        body: dict[str, Any],
        api_key: str,
    ) -> dict[str, Any]:
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
        result: dict[str, Any] = resp.json()
        return result


# ---------------------------------------------------------------------- helpers


class _StreamAccumulator:
    """Stateful Anthropic SSE event reducer.

    Anthropic emits per-block events:
      message_start, content_block_start, content_block_delta (text or
      input_json), content_block_stop, message_delta, message_stop.
    Tool-use input arrives as a sequence of `input_json_delta` partials
    that must be concatenated and JSON-parsed at content_block_stop.
    """

    def __init__(self) -> None:
        self._open_blocks: dict[int, dict[str, Any]] = {}
        self.tool_calls: list[ToolCall] = []
        self.finish_reason: str | None = None
        self._prompt_tokens = 0
        self._completion_tokens = 0

    @property
    def usage(self) -> tuple[int, int]:
        return self._prompt_tokens, self._completion_tokens

    async def feed(self, event: dict[str, Any]) -> AsyncIterator[CompletionEvent]:
        et = event.get("type")
        if et == "message_start":
            usage = event.get("message", {}).get("usage", {})
            self._prompt_tokens = int(usage.get("input_tokens", 0))
            self._completion_tokens = int(usage.get("output_tokens", 0))
        elif et == "content_block_start":
            idx = int(event.get("index", -1))
            block = event.get("content_block", {}) or {}
            self._open_blocks[idx] = {
                "type": block.get("type"),
                "id": block.get("id"),
                "name": block.get("name"),
                "input_buffer": "",
            }
        elif et == "content_block_delta":
            idx = int(event.get("index", -1))
            delta = event.get("delta", {}) or {}
            dt = delta.get("type")
            if dt == "text_delta":
                text = delta.get("text", "") or ""
                if text:
                    yield CompletionEvent(type="text_delta", payload={"text": text})
            elif dt == "input_json_delta":
                block = self._open_blocks.get(idx)
                if block is not None and block.get("type") == "tool_use":
                    block["input_buffer"] += delta.get("partial_json", "") or ""
        elif et == "content_block_stop":
            idx = int(event.get("index", -1))
            block = self._open_blocks.pop(idx, None)
            if block is not None and block.get("type") == "tool_use":
                arguments = _parse_input_json(block.get("input_buffer") or "")
                tc = ToolCall(
                    id=str(block.get("id") or f"tu_{idx}"),
                    name=str(block.get("name") or ""),
                    arguments=arguments,
                )
                self.tool_calls.append(tc)
                yield CompletionEvent(
                    type="tool_call",
                    payload={"id": tc.id, "name": tc.name, "arguments": tc.arguments},
                )
        elif et == "message_delta":
            delta = event.get("delta", {}) or {}
            if delta.get("stop_reason"):
                self.finish_reason = _normalize_stop_reason(delta.get("stop_reason"))
            usage = event.get("usage", {}) or {}
            if "output_tokens" in usage:
                self._completion_tokens = int(usage["output_tokens"])
            if "input_tokens" in usage:
                self._prompt_tokens = int(usage["input_tokens"])
        elif et == "error":
            err = event.get("error", {}) or {}
            yield CompletionEvent(
                type="error",
                payload={"message": err.get("message") or "stream error"},
            )


def _serialize_message(m: Message) -> dict[str, Any]:
    if m.role == "assistant" and m.tool_calls:
        content: list[dict[str, Any]] = []
        if m.content:
            content.append({"type": "text", "text": m.content})
        for tc in m.tool_calls:
            content.append(
                {
                    "type": "tool_use",
                    "id": tc.id,
                    "name": tc.name,
                    "input": tc.arguments,
                }
            )
        return {"role": "assistant", "content": content}
    if m.role == "tool":
        return {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": m.tool_call_id,
                    "content": m.content,
                }
            ],
        }
    role = "user" if m.role == "user" else "assistant"
    return {"role": role, "content": m.content}


def _parse_content_blocks(
    blocks: list[dict[str, Any]],
) -> tuple[str, list[ToolCall]]:
    text = ""
    tool_calls: list[ToolCall] = []
    for block in blocks:
        bt = block.get("type")
        if bt == "text":
            text += block.get("text", "") or ""
        elif bt == "tool_use":
            tool_calls.append(
                ToolCall(
                    id=str(block.get("id") or ""),
                    name=str(block.get("name") or ""),
                    arguments=block.get("input") or {},
                )
            )
    return text, tool_calls


def _parse_input_json(buf: str) -> dict[str, Any]:
    if not buf:
        return {}
    try:
        parsed = json.loads(buf)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _normalize_stop_reason(raw: str | None) -> str:
    if raw == "tool_use":
        return "tool_use"
    if raw == "max_tokens":
        return "length"
    if raw == "end_turn" or raw is None:
        return "stop"
    return raw


def _cost_cents(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    p = PRICING_CENTS_PER_MTOK.get(model, {"prompt": 100.0, "completion": 500.0})
    return (prompt_tokens / 1_000_000) * p["prompt"] + (
        completion_tokens / 1_000_000
    ) * p["completion"]
