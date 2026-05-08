from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from app.chat.providers.base import CompletionEvent
from app.core.streaming import _serialize_event, sse_response


def test_serialize_event_text_delta() -> None:
    ev = CompletionEvent(type="text_delta", payload={"text": "hello"})
    line = _serialize_event(ev)
    assert line.startswith("data: ")
    assert line.endswith("\n\n")
    assert '"text": "hello"' in line
    assert '"type": "text_delta"' in line


def test_serialize_event_tool_call() -> None:
    ev = CompletionEvent(
        type="tool_call",
        payload={"id": "tu_1", "name": "get_price_move", "arguments": {"x": 1}},
    )
    line = _serialize_event(ev)
    assert '"type": "tool_call"' in line
    assert '"id": "tu_1"' in line


def test_serialize_event_done() -> None:
    ev = CompletionEvent(
        type="done",
        payload={"finish_reason": "stop", "cost_cents": 0.42, "engine_call_ids": []},
    )
    line = _serialize_event(ev)
    assert '"type": "done"' in line
    assert '"finish_reason": "stop"' in line


@pytest.mark.asyncio
async def test_sse_response_emits_lines() -> None:
    async def events() -> AsyncIterator[CompletionEvent]:
        yield CompletionEvent(type="text_delta", payload={"text": "hi"})
        yield CompletionEvent(type="done", payload={"finish_reason": "stop"})

    resp = sse_response(events())
    assert resp.media_type == "text/event-stream"
    body = b""
    async for chunk in resp.body_iterator:
        body += chunk if isinstance(chunk, bytes) else chunk.encode()
    decoded = body.decode("utf-8")
    parts = [p for p in decoded.split("\n\n") if p]
    assert len(parts) == 2
    assert parts[0].startswith("data: ")
    assert '"type": "text_delta"' in parts[0]
    assert '"type": "done"' in parts[1]
