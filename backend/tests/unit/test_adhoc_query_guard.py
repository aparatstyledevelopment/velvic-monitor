import pytest

from app.core.errors import ValidationError
from app.engine.adhoc_query import MAX_LIMIT, validate_sql


# ---------- happy paths ----------


def test_simple_select_passes() -> None:
    out = validate_sql("SELECT id, ticker FROM company_v WHERE country = 'SE'")
    assert "company_v" in out
    assert "LIMIT" in out.upper()


def test_aggregation_passes() -> None:
    out = validate_sql(
        "SELECT count(*) AS n, source FROM news_item_v GROUP BY source"
    )
    assert "count" in out.lower()


def test_explicit_limit_below_cap_preserved() -> None:
    out = validate_sql("SELECT id FROM company_v LIMIT 50")
    assert "LIMIT 50" in out.upper()


def test_explicit_limit_above_cap_clamped() -> None:
    out = validate_sql("SELECT id FROM company_v LIMIT 9999")
    assert f"LIMIT {MAX_LIMIT}" in out.upper()


def test_join_across_allowed_views_passes() -> None:
    out = validate_sql(
        "SELECT c.ticker, p.close FROM company_v c "
        "JOIN price_bar_v p ON p.company_id = c.id "
        "ORDER BY p.trading_date DESC"
    )
    assert "company_v" in out and "price_bar_v" in out


# ---------- guards ----------


def test_insert_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_sql("INSERT INTO company_v VALUES (1, 'X')")


def test_update_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_sql("UPDATE company_v SET ticker='X' WHERE id=1")


def test_delete_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_sql("DELETE FROM company_v WHERE id=1")


def test_drop_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_sql("DROP TABLE company_v")


def test_select_from_disallowed_table_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_sql("SELECT * FROM company")  # base table, not the _v view


def test_dangerous_function_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_sql("SELECT pg_read_file('/etc/passwd')")


def test_empty_input_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_sql("")


def test_garbage_input_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_sql("hello world")
