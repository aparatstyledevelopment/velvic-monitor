from __future__ import annotations

from datetime import date as Date
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class CitationSpanOut(BaseModel):
    start_char: int
    end_char: int
    engine_call_id: str


class BriefingOut(BaseModel):
    company_id: int
    module: str
    as_of_date: Date
    narrative: str
    smart_chips: list[str]
    citation_spans: list[CitationSpanOut]
    engine_call_ids: list[str]
    llm_provider: str
    llm_model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    cost_cents: Decimal | None
    generated_at: datetime


class EngineCallOut(BaseModel):
    engine_call_id: str
    tool_name: str
    module: str
    params: dict[str, Any]
    data: dict[str, Any]
    sources: list[dict[str, Any]]
    status: str
    latency_ms: int
    engine_version: str
    computed_at: datetime
