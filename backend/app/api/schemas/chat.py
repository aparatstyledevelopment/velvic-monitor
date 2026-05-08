from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ChatThreadCreate(BaseModel):
    company_id: int
    title: str | None = None


class ChatThreadOut(BaseModel):
    id: UUID
    company_id: int
    user_id: UUID
    title: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class CitationSpanOut(BaseModel):
    start_char: int
    end_char: int
    engine_call_id: str


class ChatTurnOut(BaseModel):
    id: UUID
    thread_id: UUID
    idx: int
    role: str
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    tool_name: str | None = None
    citation_spans: list[CitationSpanOut] = Field(default_factory=list)
    llm_provider: str | None = None
    llm_model: str | None = None
    prompt_tokens: int
    completion_tokens: int
    cost_cents: Decimal
    finish_reason: str | None = None
    warning: str | None = None
    created_at: datetime


class ChatThreadDetail(ChatThreadOut):
    turns: list[ChatTurnOut] = Field(default_factory=list)


class ChatTurnIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
