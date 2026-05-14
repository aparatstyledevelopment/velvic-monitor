"""Topic gate: cheap-classifier guard in front of the expensive tool loop.

Runs a single small-model completion on the user's latest message,
scoped to the thread's company. Defaults to ON_TOPIC; only refuses on
hard violations (jailbreaks, trade recs, fully off-topic prompts).

Output contract is JSON:
  {"on_topic": true}
  {"on_topic": false, "reason": "<short reason>"}
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.chat.anthropic_messages_client import call_messages
from app.chat.prompts import REFUSAL_TEMPLATE, render_topic_gate_system
from app.core.logging import logger


@dataclass(frozen=True)
class TopicDecision:
    on_topic: bool
    reason: str  # empty when on-topic


CLASSIFIER_MAX_TOKENS = 96


async def classify(
    message: str,
    *,
    company_name: str,
    ticker: str,
    model: str | None = None,
) -> TopicDecision:
    """Return ON_TOPIC / OFF_TOPIC decision for `message`.

    The system prompt is rendered with the thread's company so the
    classifier knows what "in scope" means for this conversation.
    """
    try:
        response = await call_messages(
            system=render_topic_gate_system(
                company_name=company_name, ticker=ticker
            ),
            user=message,
            max_tokens=CLASSIFIER_MAX_TOKENS,
            temperature=0.0,
            model=model,
        )
    except RuntimeError as e:
        logger.warning("topic_gate_unavailable", error=str(e))
        return TopicDecision(on_topic=True, reason="")
    return _parse_decision(response.text)


def _parse_decision(raw: str) -> TopicDecision:
    text = _strip_code_fence(raw.strip())
    try:
        payload: Any = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("topic_gate_unparseable", raw=raw[:200])
        # Fail open: prefer letting the prompt through over a false refusal.
        return TopicDecision(on_topic=True, reason="")

    if not isinstance(payload, dict):
        logger.warning("topic_gate_unparseable", raw=raw[:200])
        return TopicDecision(on_topic=True, reason="")

    on_topic = payload.get("on_topic")
    if not isinstance(on_topic, bool):
        logger.warning("topic_gate_unparseable", raw=raw[:200])
        return TopicDecision(on_topic=True, reason="")

    if on_topic:
        return TopicDecision(on_topic=True, reason="")

    reason_raw = payload.get("reason")
    reason = (
        reason_raw.strip()
        if isinstance(reason_raw, str) and reason_raw.strip()
        else "out of scope."
    )
    return TopicDecision(on_topic=False, reason=reason)


def _strip_code_fence(text: str) -> str:
    if not text.startswith("```"):
        return text
    stripped = text.strip("`")
    nl = stripped.find("\n")
    if nl == -1:
        return stripped
    head = stripped[:nl].strip().lower()
    if head in ("json", ""):
        return stripped[nl + 1 :].strip()
    return stripped


def render_refusal(*, company_name: str, reason: str) -> str:
    cleaned = reason.rstrip(".")
    sentence = (cleaned + ".") if cleaned else "That topic is outside scope."
    return REFUSAL_TEMPLATE.format(company_name=company_name, reason=sentence)
