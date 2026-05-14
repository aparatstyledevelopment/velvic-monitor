"""Auto-rename a thread after its first round-trip.

The frontend creates threads with the user's first message as the title;
that's fine for the very first paint but not what you want when the
sidebar fills up with verbatim sentences. After the first assistant turn
lands, this module asks a small model for a 3-5 word title and writes it
back to the thread row.

Idempotent: runs only when the existing title still looks like the raw
user message (the heuristic check `_looks_like_raw_user_message`).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.chat.anthropic_messages_client import MessagesResponse, call_messages
from app.core.logging import logger


@dataclass(frozen=True)
class TitleResult:
    title: str | None
    response: MessagesResponse | None

_PROMPT = (
    "Summarise this IR analyst exchange as a 3-5 word title. "
    "Use sentence case, no quotes, no trailing punctuation, no emoji. "
    "Output ONLY the title.\n\n"
    "User: {user}\n"
    "Assistant: {assistant}"
)


async def generate_title(
    *, user_message: str, assistant_text: str
) -> TitleResult:
    """Return a short title (or None) plus the raw response for logging."""
    try:
        response = await call_messages(
            system="You write tight 3-5 word titles for IR chat threads.",
            user=_PROMPT.format(
                user=user_message[:400],
                assistant=assistant_text[:600],
            ),
            max_tokens=24,
            temperature=0.0,
        )
    except Exception as e:  # network, parse, missing key — all non-fatal
        logger.warning("thread_title_failed", error=str(e))
        return TitleResult(title=None, response=None)
    return TitleResult(title=_clean(response.text), response=response)


def _clean(raw: str) -> str | None:
    text = raw.strip().splitlines()[0] if raw.strip() else ""
    text = text.strip().strip('"').strip("'").rstrip(".!?")
    if not text:
        return None
    words = text.split()
    if len(words) > 6:
        text = " ".join(words[:6])
    return text


def looks_like_raw_user_message(title: str, user_message: str) -> bool:
    """Heuristic: is the thread still titled with the user's first message?"""
    t = title.strip().rstrip("…").rstrip()
    u = user_message.strip()
    return t == u or u.startswith(t) or t.startswith(u[:40])
