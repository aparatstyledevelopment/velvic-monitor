from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import models so Base.metadata is populated.
from app.auth import models as _auth_models  # noqa: F401
from app.chat import models as _chat_models  # noqa: F401
from app.core.config import get_settings
from app.core.db import Base
from app.crawlers import models as _crawler_models  # noqa: F401
from app.engine import models as _engine_models  # noqa: F401
from app.ingestion import models as _ingestion_models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _sync_url(url: str) -> str:
    """Translate the asyncpg-style URL to one psycopg accepts for offline mode."""
    sync = url.replace("+asyncpg", "")
    # asyncpg uses ?ssl=require; psycopg uses ?sslmode=require.
    sync = sync.replace("ssl=", "sslmode=")
    return sync


def run_migrations_offline() -> None:
    url = _sync_url(get_settings().database_url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _sanitized(url: str) -> str:
    """URL with credentials redacted, for one-line debug output."""
    from urllib.parse import urlparse, urlunparse

    parsed = urlparse(url)
    netloc = f"***:***@{parsed.hostname or '?'}:{parsed.port or '?'}"
    return urlunparse(parsed._replace(netloc=netloc))


async def run_migrations_online() -> None:
    settings = get_settings()
    print(f"[alembic] connecting to {_sanitized(settings.database_url)}", flush=True)
    cfg = config.get_section(config.config_ini_section) or {}
    cfg["sqlalchemy.url"] = settings.database_url
    connectable = async_engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
