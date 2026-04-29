from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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


@lru_cache
def get_settings() -> Settings:
    return Settings()
