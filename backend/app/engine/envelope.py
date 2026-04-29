"""Engine result envelope.

The Engine/Narrator contract: every Engine tool returns an EngineResult[T]
carrying a content-addressed engine_call_id, a typed data payload, and a
list of SourceRef provenance markers. The LLM cites results by id; the
Source pane renders the SourceRefs.

See ADR 0003.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class SourceRef(BaseModel):
    """Provenance marker pointing back to Tier-1 raw row(s) or external URL."""

    id: str
    kind: str
    description: str
    url: str | None = None
    row_ids: list[int] = Field(default_factory=list)
    fetched_at: datetime | None = None


class EngineResult(BaseModel, Generic[T]):
    engine_call_id: str
    tool_name: str
    module: str
    params: dict[str, Any]
    data: T
    sources: list[SourceRef] = Field(default_factory=list)
    computed_at: datetime
    engine_version: str
    latency_ms: int


def hash_call_id(*, tool_name: str, params: dict[str, Any]) -> str:
    """Content-address an engine call. Stable across runs for the same inputs.

    Same tool_name + same canonical params -> same id. Used for cache reuse
    in the Engine ledger.
    """
    blob = json.dumps({"tool": tool_name, "params": params}, sort_keys=True, default=str)
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return f"ec_{digest[:12]}"
