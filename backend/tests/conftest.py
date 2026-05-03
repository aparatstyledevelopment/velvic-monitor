"""Shared pytest fixtures.

Most tests in Phase 0 are unit tests with no DB dependency. Integration
fixtures (Postgres, Redis) come online in Phase 1 alongside the data layer.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _isolate_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin known-good values so tests don't read the developer's .env.local."""
    monkeypatch.setenv("ENV", "local")
    monkeypatch.setenv("JWT_SECRET", "test-only-secret")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+asyncpg://velvic:velvic@localhost:5432/velvic_test"
    )
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/15")
    # Bypass Settings() lru_cache between tests
    from app.core import config

    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()
    os.environ.pop("ENV", None)
