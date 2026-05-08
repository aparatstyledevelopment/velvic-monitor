"""Topic gate: cheap-classifier guard in front of the expensive tool loop.

Runs a single small-model completion on the user's latest message and
either returns ON_TOPIC (orchestrator proceeds) or OFF_TOPIC with a short
reason (orchestrator emits the canonical refusal).

The classifier is provider-agnostic: takes any LLMProvider. In production
the orchestrator wires this to the cheapest model available on the org's
preferred provider (e.g. Anthropic Haiku).

Parser tolerance: classifiers occasionally wrap the verdict in markdown
(`**ON_TOPIC**`), quotes, or a leading sentence. We search for the token
anywhere in the response and fail-closed on ambiguity.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.chat.prompts import REFUSAL_TEMPLATE, TOPIC_GATE_SYSTEM
from app.chat.providers.base import LLMProvider, Message
from app.core.logging import logger


@dataclass(frozen=True)
class TopicDecision:
    on_topic: bool
    reason: str  # empty when on-topic


CLASSIFIER_MAX_TOKENS = 64

_ON_TOPIC_RE = re.compile(r"\bON[_ ]TOPIC\b", re.IGNORECASE)
_OFF_TOPIC_RE = re.compile(r"\bOFF[_ ]TOPIC\b", re.IGNORECASE)
_OFF_TOPIC_REASON_RE = re.compile(
    r"\bOFF[_ ]TOPIC\s*:?\s*(.*)", re.IGNORECASE | re.DOTALL
)


async def classify(
    provider: LLMProvider,
    message: str,
    *,
    model: str | None = None,
) -> TopicDecision:
    """Return ON_TOPIC / OFF_TOPIC decision for `message`."""
    response = await provider.complete(
        system=TOPIC_GATE_SYSTEM,
        messages=[Message(role="user", content=message)],
        max_tokens=CLASSIFIER_MAX_TOKENS,
        temperature=0.0,
        model=model,
    )
    return _parse_decision(response.text)


def _parse_decision(raw: str) -> TopicDecision:
    text = raw.strip()
    has_on = bool(_ON_TOPIC_RE.search(text))
    has_off = bool(_OFF_TOPIC_RE.search(text))

    if has_off and not has_on:
        m = _OFF_TOPIC_REASON_RE.search(text)
        reason_raw = m.group(1).strip() if m else ""
        # First non-empty line (strip any trailing markdown like `**`).
        first = next(
            (line.strip() for line in reason_raw.splitlines() if line.strip()), ""
        )
        reason = re.sub(r"[`*_\"]+$", "", first).strip() or "out of scope."
        return TopicDecision(on_topic=False, reason=reason)

    if has_on and not has_off:
        return TopicDecision(on_topic=True, reason="")

    if has_on and has_off:
        logger.warning("topic_gate_ambiguous", raw=text[:200])
        return TopicDecision(on_topic=False, reason="classifier output ambiguous.")

    logger.warning("topic_gate_unparseable", raw=text[:200])
    return TopicDecision(on_topic=False, reason="classifier output unparseable.")


def render_refusal(*, company_name: str, reason: str) -> str:
    cleaned = reason.rstrip(".")
    sentence = (cleaned + ".") if cleaned else "That topic is outside scope."
    return REFUSAL_TEMPLATE.format(company_name=company_name, reason=sentence)
