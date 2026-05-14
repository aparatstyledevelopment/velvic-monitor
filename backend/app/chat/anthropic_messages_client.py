"""One-shot Anthropic Messages helper.

The chat orchestrator drives the Claude Agent SDK (ADR 0009); single-shot
LLM calls — the topic gate classifier and the briefing/news-summary
composer — don't need the agent loop, so they talk to the Messages API
through this thin httpx wrapper instead of paying the subprocess cost of
the SDK.

Pricing is kept here because both call sites need to record cost on
their persisted rows.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.config import get_settings

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
PRICING_CENTS_PER_MTOK: dict[str, dict[str, float]] = {
    "claude-haiku-4-5-20251001": {"prompt": 100.0, "completion": 500.0},
    "claude-sonnet-4-6": {"prompt": 300.0, "completion": 1500.0},
    "claude-opus-4-7": {"prompt": 1500.0, "completion": 7500.0},
}
_BASE_URL = "https://api.anthropic.com/v1/messages"


@dataclass(frozen=True)
class MessagesResponse:
    text: str
    prompt_tokens: int
    completion_tokens: int
    cost_cents: float
    model: str


def cost_cents(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    p = PRICING_CENTS_PER_MTOK.get(model, {"prompt": 100.0, "completion": 500.0})
    return (prompt_tokens / 1_000_000) * p["prompt"] + (
        completion_tokens / 1_000_000
    ) * p["completion"]


async def call_messages(
    *,
    system: str,
    user: str,
    max_tokens: int = 1024,
    temperature: float = 0.0,
    model: str | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> MessagesResponse:
    """Single-turn POST /v1/messages with a system + user prompt.

    Raises RuntimeError when ANTHROPIC_API_KEY is unset. Callers that
    need a graceful fallback (mock mode for local backfill) must catch
    that themselves.
    """
    api_key = get_settings().anthropic_api_key
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")

    chosen_model = model or DEFAULT_MODEL
    body: dict[str, object] = {
        "model": chosen_model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    if http_client is not None:
        data = await _post(http_client, body, headers)
    else:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            data = await _post(client, body, headers)

    raw_content = data.get("content")
    blocks: list[dict[str, object]] = raw_content if isinstance(raw_content, list) else []
    text = _extract_text(blocks)
    raw_usage = data.get("usage")
    usage: dict[str, object] = raw_usage if isinstance(raw_usage, dict) else {}
    prompt_tokens = _coerce_int(usage.get("input_tokens"))
    completion_tokens = _coerce_int(usage.get("output_tokens"))
    return MessagesResponse(
        text=text,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_cents=cost_cents(chosen_model, prompt_tokens, completion_tokens),
        model=chosen_model,
    )


async def _post(
    client: httpx.AsyncClient,
    body: dict[str, object],
    headers: dict[str, str],
) -> dict[str, object]:
    resp = await client.post(_BASE_URL, json=body, headers=headers)
    resp.raise_for_status()
    result: dict[str, object] = resp.json()
    return result


def _extract_text(blocks: list[dict[str, object]]) -> str:
    out: list[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            val = block.get("text", "")
            if isinstance(val, str):
                out.append(val)
    return "".join(out)


def _coerce_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0
