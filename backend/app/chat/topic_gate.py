"""Topic gate: cheap-classifier guard in front of the expensive tool loop.

Runs a single small-model completion on the user's latest message and
either returns ON_TOPIC (orchestrator proceeds) or OFF_TOPIC with a short
reason (orchestrator emits the canonical refusal).

Output contract is JSON:
  {"on_topic": true}
  {"on_topic": false, "reason": "<short reason>"}
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.chat.anthropic_messages_client import call_messages
from app.chat.prompts import REFUSAL_TEMPLATE, TOPIC_GATE_SYSTEM
from app.core.logging import logger


@dataclass(frozen=True)
class TopicDecision:
    on_topic: bool
    reason: str  # empty when on-topic


CLASSIFIER_MAX_TOKENS = 96


async def classify(message: str, *, model: str | None = None) -> TopicDecision:
    """Return ON_TOPIC / OFF_TOPIC decision for `message`."""
    try:
        response = await call_messages(
            system=TOPIC_GATE_SYSTEM,
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
        return TopicDecision(on_topic=False, reason="classifier output unparseable.")

    if not isinstance(payload, dict):
        logger.warning("topic_gate_unparseable", raw=raw[:200])
        return TopicDecision(on_topic=False, reason="classifier output not an object.")

    on_topic = payload.get("on_topic")
    if not isinstance(on_topic, bool):
        logger.warning("topic_gate_unparseable", raw=raw[:200])
        return TopicDecision(
            on_topic=False, reason="classifier missing on_topic boolean."
        )

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
    """Tolerate ```json ... ``` wrappers some models emit despite the prompt."""
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
