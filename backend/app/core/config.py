from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_async_db_url(raw: str) -> str:
    """Accept the URL shape DO Managed Postgres injects and coerce to asyncpg.

    DO injects `postgresql://user:pw@host:port/db?sslmode=require`. SQLAlchemy
    with asyncpg needs `postgresql+asyncpg://...?ssl=require` (asyncpg uses the
    `ssl` query param, not psycopg's `sslmode`).
    """
    if raw.startswith("postgresql://") and "+asyncpg" not in raw:
        raw = "postgresql+asyncpg://" + raw[len("postgresql://") :]
    if "sslmode=" in raw:
        raw = raw.replace("sslmode=", "ssl=")
    return raw


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Literal["local", "staging", "production"] = "local"
    engine_version: str = Field(default="v0.1.0+dev")

    database_url: str = "postgresql+asyncpg://velvic:velvic@localhost:5432/velvic"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "dev-only-not-for-production"
    jwt_access_ttl_seconds: int = 60 * 15
    jwt_refresh_ttl_seconds: int = 60 * 60 * 24 * 7

    encryption_key: str = "dev-only-32-byte-key-not-for-prod-use"

    cors_origins: list[str] = ["http://localhost:5173"]

    sentry_dsn: str | None = None
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None

    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    google_api_key: str | None = None
    fred_api_key: str | None = None
    postmark_token: str | None = None

    @field_validator("database_url", mode="before")
    @classmethod
    def _coerce_database_url(cls, v: object) -> object:
        if isinstance(v, str):
            return _normalize_async_db_url(v)
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
