"""Provider factory. Picks an implementation by name and provides a
hook for tests to inject overrides.
"""

from __future__ import annotations

from app.chat.providers.anthropic import AnthropicProvider
from app.chat.providers.base import LLMProvider
from app.chat.providers.mock import MockProvider

_OVERRIDE: LLMProvider | None = None


def set_override(provider: LLMProvider | None) -> None:
    """Tests call this to inject a MockProvider; pass None to clear."""
    global _OVERRIDE
    _OVERRIDE = provider


def get_provider(name: str) -> LLMProvider:
    if _OVERRIDE is not None:
        return _OVERRIDE
    if name == "anthropic":
        return AnthropicProvider()
    if name == "mock":
        return MockProvider(text="(mock provider has no default response)")
    raise ValueError(f"unsupported provider: {name}")
