"""Engine call ledger persistence.

Every Engine tool invocation writes one row to engine_call. Content-addressed
caching: same (tool, canonical_params) -> same id, so re-invocations within
a window may be served from cache rather than recomputed.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.engine.envelope import EngineResult, SourceRef
from app.engine.models import EngineCall


async def get_cached(session: AsyncSession, engine_call_id: str) -> EngineCall | None:
    return await session.get(EngineCall, engine_call_id)


async def persist(session: AsyncSession, result: EngineResult[Any]) -> EngineCall:
    """Insert (or no-op if already present) an engine_call row."""
    existing = await get_cached(session, result.engine_call_id)
    if existing is not None:
        return existing
    row = EngineCall(
        id=result.engine_call_id,
        tool_name=result.tool_name,
        module=result.module,
        params=result.params,
        result=result.data.model_dump(mode="json"),
        source_refs=[s.model_dump(mode="json") for s in result.sources],
        status="ok",
        latency_ms=result.latency_ms,
        engine_version=result.engine_version,
    )
    session.add(row)
    await session.flush()
    return row


async def persist_error(
    session: AsyncSession,
    *,
    engine_call_id: str,
    tool_name: str,
    module: str,
    params: dict[str, Any],
    error: str,
    latency_ms: int,
    status: str = "error",
) -> EngineCall:
    settings = get_settings()
    row = EngineCall(
        id=engine_call_id,
        tool_name=tool_name,
        module=module,
        params=params,
        result={},
        source_refs=[],
        status=status,
        error_message=error[:2000],
        latency_ms=latency_ms,
        engine_version=settings.engine_version,
    )
    session.add(row)
    await session.flush()
    return row


def envelope_from_row(row: EngineCall) -> dict[str, Any]:
    """Reconstruct a JSON-serializable view of an engine call (for the API/Source pane)."""
    return {
        "engine_call_id": row.id,
        "tool_name": row.tool_name,
        "module": row.module,
        "params": row.params,
        "data": row.result,
        "sources": row.source_refs,
        "computed_at": row.called_at.isoformat() if row.called_at else None,
        "engine_version": row.engine_version,
        "latency_ms": row.latency_ms,
        "status": row.status,
    }


_ = SourceRef  # silence unused import warnings; symmetry with envelope module
