"""Topic gate: cheap-classifier guard in front of the expensive tool loop.

Runs a single small-model completion on the user's latest message and
either returns ON_TOPIC (orchestrator proceeds) or OFF_TOPIC with a short
reason (orchestrator emits the canonical refusal).

The classifier is provider-agnostic: takes any LLMProvider. In production
the orchestrator wires this to the cheapest model available on the org's
preferred provider (e.g. Anthropic Haiku).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.chat.prompts import REFUSAL_TEMPLATE, TOPIC_GATE_SYSTEM
from app.chat.providers.base import LLMProvider, Message


@dataclass(frozen=True)
class TopicDecision:
    on_topic: bool
    reason: str  # empty when on-topic


CLASSIFIER_MAX_TOKENS = 32


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
    if text.upper().startswith("ON_TOPIC"):
        return TopicDecision(on_topic=True, reason="")
    if text.upper().startswith("OFF_TOPIC"):
        # `OFF_TOPIC: <reason>` — strip the prefix and any colon.
        rest = text.split(":", 1)
        reason = rest[1].strip() if len(rest) == 2 else ""
        return TopicDecision(on_topic=False, reason=reason or "out of scope.")
    # Unparseable verdicts fail-closed to off-topic; safer than the model
    # accidentally bypassing the gate with a hallucinated answer.
    return TopicDecision(on_topic=False, reason="classifier output unparseable.")


def render_refusal(*, company_name: str, reason: str) -> str:
    cleaned = reason.rstrip(".")
    sentence = (cleaned + ".") if cleaned else "That topic is outside scope."
    return REFUSAL_TEMPLATE.format(company_name=company_name, reason=sentence)
