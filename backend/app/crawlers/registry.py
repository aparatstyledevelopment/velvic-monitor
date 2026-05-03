from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.crawlers.base import BaseCrawler

# Crawlers are generic over their parsed-row type; the registry stores them as
# BaseCrawler[Any] since the registry consumer (Celery task) doesn't care.
_REGISTRY: dict[str, Callable[[], BaseCrawler[Any]]] = {}


def register(
    name: str,
) -> Callable[[Callable[[], BaseCrawler[Any]]], Callable[[], BaseCrawler[Any]]]:
    def deco(
        factory: Callable[[], BaseCrawler[Any]],
    ) -> Callable[[], BaseCrawler[Any]]:
        if name in _REGISTRY:
            raise ValueError(f"crawler already registered: {name}")
        _REGISTRY[name] = factory
        return factory

    return deco


def build(name: str) -> BaseCrawler[Any]:
    if name not in _REGISTRY:
        raise KeyError(f"unknown crawler: {name}")
    return _REGISTRY[name]()


def all_names() -> list[str]:
    return sorted(_REGISTRY.keys())
