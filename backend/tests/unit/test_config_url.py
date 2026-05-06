from app.core.config import _normalize_async_db_url


def test_passthrough_already_async() -> None:
    url = "postgresql+asyncpg://u:p@h:5432/db"
    assert _normalize_async_db_url(url) == url


def test_coerces_plain_postgres_to_asyncpg() -> None:
    url = "postgresql://u:p@h:5432/db"
    assert _normalize_async_db_url(url) == "postgresql+asyncpg://u:p@h:5432/db"


def test_translates_sslmode_to_ssl_for_asyncpg() -> None:
    url = "postgresql://u:p@h:5432/db?sslmode=require"
    assert _normalize_async_db_url(url) == (
        "postgresql+asyncpg://u:p@h:5432/db?ssl=require"
    )


def test_keeps_existing_ssl_param() -> None:
    url = "postgresql+asyncpg://u:p@h:5432/db?ssl=require"
    assert _normalize_async_db_url(url) == url


def test_handles_complex_query_string() -> None:
    url = "postgresql://u:p@h:5432/db?sslmode=require&connect_timeout=10"
    out = _normalize_async_db_url(url)
    assert out.startswith("postgresql+asyncpg://")
    assert "ssl=require" in out
    assert "connect_timeout=10" in out
