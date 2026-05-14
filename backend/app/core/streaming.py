"""Server-sent events (SSE) helpers.

Wire format:
  data: {"type": "<event_type>", ...payload fields}\n\n

The chat orchestrator yields CompletionEvent objects with `type` and a
JSON-serializable `payload` dict; `sse_response` flattens them into the
`data:` lines a browser EventSource can consume directly.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi.responses import StreamingResponse

from app.chat.types import CompletionEvent

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",  # disable nginx response buffering
}


def sse_response(events: AsyncIterator[CompletionEvent]) -> StreamingResponse:
    return StreamingResponse(
        _format_events(events),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


async def _format_events(
    events: AsyncIterator[CompletionEvent],
) -> AsyncIterator[bytes]:
    async for ev in events:
        line = _serialize_event(ev)
        yield line.encode("utf-8")


def _serialize_event(ev: CompletionEvent) -> str:
    payload: dict[str, Any] = {"type": ev.type}
    payload.update(ev.payload)
    return f"data: {json.dumps(payload, default=str)}\n\n"
