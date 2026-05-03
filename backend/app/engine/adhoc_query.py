"""ad_hoc_query: a guarded SQL escape hatch for the LLM.

The LLM writes SQL against the analytics views; we validate the AST
(SELECT only, allow-listed views, no dangerous functions, LIMIT capped),
then run it under a session-level SET ROLE engine_readonly with a
statement timeout. The Postgres role itself is also least-privilege
(see migration 0002), giving us defense-in-depth.

Approach: parse with sqlglot, walk the AST, reject anything not on the
allow-list. Returns up to 1000 rows.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import sqlglot
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationError
from app.engine.drivers.types import QueryResult, QueryRow
from app.engine.envelope import EngineResult, SourceRef
from app.engine.registry import engine_tool

ALLOWED_VIEWS: frozenset[str] = frozenset(
    {
        "company_v",
        "price_bar_v",
        "news_item_v",
        "macro_observation_v",
        "peer_relationship_v",
    }
)
ALLOWED_FUNCTIONS: frozenset[str] = frozenset(
    {
        "count",
        "sum",
        "avg",
        "min",
        "max",
        "round",
        "abs",
        "coalesce",
        "lower",
        "upper",
        "now",
        "current_date",
        "extract",
        "date_trunc",
    }
)
MAX_LIMIT = 1000
STATEMENT_TIMEOUT_MS = 5_000


def validate_sql(sql: str) -> str:
    """Parse + validate. Returns the (possibly LIMIT-injected) SQL."""
    try:
        parsed = sqlglot.parse_one(sql, read="postgres")
    except sqlglot.errors.ParseError as e:
        raise ValidationError(f"sql parse error: {e}") from e
    if parsed is None:
        raise ValidationError("empty SQL")

    # Top-level must be a Select
    select_node = parsed.find(sqlglot.exp.Select)
    if select_node is None or parsed.key != "select":
        raise ValidationError("only SELECT statements are permitted")

    # No DML / DDL / utility statements
    forbidden = (
        sqlglot.exp.Insert,
        sqlglot.exp.Update,
        sqlglot.exp.Delete,
        sqlglot.exp.Drop,
        sqlglot.exp.Create,
        sqlglot.exp.Alter,
        sqlglot.exp.Command,
    )
    # sqlglot 25.x: walk() yields Expression nodes directly.
    for node in parsed.walk():
        if isinstance(node, forbidden):
            raise ValidationError(f"forbidden statement type: {type(node).__name__}")

    # Tables referenced must all be allow-listed views
    for table in parsed.find_all(sqlglot.exp.Table):
        name = (table.name or "").lower()
        if name not in ALLOWED_VIEWS:
            raise ValidationError(f"table not allowed: {name}")

    # Functions must be allow-listed
    for fn in parsed.find_all(sqlglot.exp.Anonymous):
        fname = (fn.this or "").lower() if isinstance(fn.this, str) else ""
        if fname and fname not in ALLOWED_FUNCTIONS:
            raise ValidationError(f"function not allowed: {fname}")

    # Inject LIMIT if absent or shrink if too large
    limit_node = parsed.args.get("limit")
    if limit_node is None:
        parsed.set(
            "limit", sqlglot.exp.Limit(expression=sqlglot.exp.Literal.number(MAX_LIMIT))
        )
    else:
        existing = limit_node.expression
        try:
            current = (
                int(existing.this)
                if isinstance(existing, sqlglot.exp.Literal)
                else MAX_LIMIT
            )
        except (TypeError, ValueError):
            current = MAX_LIMIT
        if current > MAX_LIMIT:
            parsed.set(
                "limit",
                sqlglot.exp.Limit(expression=sqlglot.exp.Literal.number(MAX_LIMIT)),
            )

    return parsed.sql(dialect="postgres")


@engine_tool(
    name="ad_hoc_query",
    module="shared",
    description=(
        "Run a read-only SQL SELECT against the analytics views. Allowed "
        "views: company_v, price_bar_v, news_item_v, macro_observation_v, "
        "peer_relationship_v. SELECT only. Maximum 1000 rows. Use only "
        "when no typed tool fits the question."
    ),
    cost_class="moderate",
)
async def ad_hoc_query(*, session: AsyncSession, sql: str) -> EngineResult[QueryResult]:
    safe_sql = validate_sql(sql)
    # Apply a statement timeout for this transaction only.
    await session.execute(text(f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}"))
    rows = (await session.execute(text(safe_sql))).mappings().all()

    columns: list[str] = list(rows[0].keys()) if rows else []
    out_rows: list[list[Any]] = []
    for r in rows[:MAX_LIMIT]:
        out_rows.append([_to_jsonable(r[c]) for c in columns])
    truncated = len(rows) >= MAX_LIMIT

    return EngineResult(
        engine_call_id="pending",
        tool_name="pending",
        module="shared",
        params={},
        data=QueryResult(
            sql=safe_sql,
            result=QueryRow(columns=columns, rows=out_rows, truncated=truncated),
        ),
        sources=[
            SourceRef(
                id="ad_hoc_query",
                kind="analytics_view",
                description="Read-only SQL against analytics views",
            )
        ],
        computed_at=datetime.now(UTC),
        engine_version="pending",
        latency_ms=0,
    )


def _to_jsonable(v: Any) -> Any:
    if v is None or isinstance(v, str | int | float | bool):
        return v
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)
