from __future__ import annotations

import json

import httpx
import pytest

from app.chat.providers.anthropic import AnthropicProvider
from app.chat.providers.base import Message, ToolCall, ToolSpec

# ---------------------------------------------------------------------- complete


@pytest.mark.asyncio
async def test_complete_parses_text_only_response() -> None:
    response_payload = {
        "content": [{"type": "text", "text": "Volvo closed lower."}],
        "usage": {"input_tokens": 12, "output_tokens": 5},
        "stop_reason": "end_turn",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=response_payload)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = AnthropicProvider(api_key="test", http_client=client)
        result = await provider.complete(
            system="sys",
            messages=[Message(role="user", content="hi")],
        )

    assert result.text == "Volvo closed lower."
    assert result.tool_calls == []
    assert result.prompt_tokens == 12
    assert result.completion_tokens == 5
    assert result.finish_reason == "stop"


@pytest.mark.asyncio
async def test_complete_parses_tool_use_blocks() -> None:
    response_payload = {
        "content": [
            {"type": "text", "text": "Let me check."},
            {
                "type": "tool_use",
                "id": "tu_1",
                "name": "get_price_move",
                "input": {"company_id": 1, "as_of": "2026-04-30"},
            },
        ],
        "usage": {"input_tokens": 50, "output_tokens": 30},
        "stop_reason": "tool_use",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=response_payload)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = AnthropicProvider(api_key="test", http_client=client)
        result = await provider.complete(
            system="sys",
            messages=[Message(role="user", content="how did volvo move?")],
            tools=[ToolSpec(name="get_price_move", description="x", input_schema={})],
        )

    assert result.text == "Let me check."
    assert result.finish_reason == "tool_use"
    assert len(result.tool_calls) == 1
    tc = result.tool_calls[0]
    assert tc.id == "tu_1"
    assert tc.name == "get_price_move"
    assert tc.arguments == {"company_id": 1, "as_of": "2026-04-30"}


@pytest.mark.asyncio
async def test_complete_serializes_tool_result_messages() -> None:
    captured_body: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_body
        captured_body = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "content": [{"type": "text", "text": "ok"}],
                "usage": {"input_tokens": 1, "output_tokens": 1},
                "stop_reason": "end_turn",
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = AnthropicProvider(api_key="test", http_client=client)
        await provider.complete(
            system="sys",
            messages=[
                Message(role="user", content="how did it move?"),
                Message(
                    role="assistant",
                    content="checking",
                    tool_calls=[
                        ToolCall(id="tu_1", name="get_price_move", arguments={"x": 1})
                    ],
                ),
                Message(
                    role="tool",
                    content='{"engine_call_id":"ec_abc"}',
                    tool_call_id="tu_1",
                ),
            ],
        )

    sent = captured_body["messages"]
    assert isinstance(sent, list)
    assert sent[1]["role"] == "assistant"
    assert any(b["type"] == "tool_use" for b in sent[1]["content"])
    assert sent[2]["role"] == "user"
    assert sent[2]["content"][0]["type"] == "tool_result"
    assert sent[2]["content"][0]["tool_use_id"] == "tu_1"


# ---------------------------------------------------------------------- streaming


def _sse(payloads: list[dict[str, object]]) -> bytes:
    """Serialize a list of event dicts as Anthropic-style SSE bytes."""
    out: list[bytes] = []
    for p in payloads:
        out.append(f"event: {p['type']}\n".encode())
        out.append(f"data: {json.dumps(p)}\n\n".encode())
    return b"".join(out)


@pytest.mark.asyncio
async def test_stream_complete_yields_text_then_tool_call_then_done() -> None:
    sse_bytes = _sse(
        [
            {
                "type": "message_start",
                "message": {"usage": {"input_tokens": 7, "output_tokens": 0}},
            },
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""},
            },
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "Let me "},
            },
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "look it up."},
            },
            {"type": "content_block_stop", "index": 0},
            {
                "type": "content_block_start",
                "index": 1,
                "content_block": {
                    "type": "tool_use",
                    "id": "tu_42",
                    "name": "get_price_move",
                },
            },
            {
                "type": "content_block_delta",
                "index": 1,
                "delta": {
                    "type": "input_json_delta",
                    "partial_json": '{"company_id":',
                },
            },
            {
                "type": "content_block_delta",
                "index": 1,
                "delta": {
                    "type": "input_json_delta",
                    "partial_json": '1,"as_of":"2026-04-30"}',
                },
            },
            {"type": "content_block_stop", "index": 1},
            {
                "type": "message_delta",
                "delta": {"stop_reason": "tool_use"},
                "usage": {"output_tokens": 22},
            },
            {"type": "message_stop"},
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=sse_bytes,
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = AnthropicProvider(api_key="test", http_client=client)
        events = []
        async for ev in provider.stream_complete(
            system="sys",
            messages=[Message(role="user", content="why did volvo move?")],
            tools=[ToolSpec(name="get_price_move", description="x", input_schema={})],
        ):
            events.append(ev)

    types = [e.type for e in events]
    assert types[:2] == ["text_delta", "text_delta"]
    assert "tool_call" in types
    assert types[-1] == "done"

    text_acc = "".join(
        str(e.payload.get("text", "")) for e in events if e.type == "text_delta"
    )
    assert text_acc == "Let me look it up."

    tc_event = next(e for e in events if e.type == "tool_call")
    assert tc_event.payload["id"] == "tu_42"
    assert tc_event.payload["arguments"] == {
        "company_id": 1,
        "as_of": "2026-04-30",
    }

    done = events[-1]
    assert done.payload["finish_reason"] == "tool_use"
    assert done.payload["prompt_tokens"] == 7
    assert done.payload["completion_tokens"] == 22
    assert len(done.payload["tool_calls"]) == 1
