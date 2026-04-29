from __future__ import annotations

from collections.abc import Callable

from app.crawlers.base import BaseCrawler

_REGISTRY: dict[str, Callable[[], BaseCrawler]] = {}


def register(name: str) -> Callable[[Callable[[], BaseCrawler]], Callable[[], BaseCrawler]]:
    def deco(factory: Callable[[], BaseCrawler]) -> Callable[[], BaseCrawler]:
        if name in _REGISTRY:
            raise ValueError(f"crawler already registered: {name}")
        _REGISTRY[name] = factory
        return factory

    return deco


def build(name: str) -> BaseCrawler:
    if name not in _REGISTRY:
        raise KeyError(f"unknown crawler: {name}")
    return _REGISTRY[name]()


def all_names() -> list[str]:
    return sorted(_REGISTRY.keys())
