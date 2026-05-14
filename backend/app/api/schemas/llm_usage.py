from __future__ import annotations

from pydantic import BaseModel


class LLMSurfaceUsage(BaseModel):
    surface: str
    call_count: int
    prompt_tokens: int
    completion_tokens: int
    cost_cents: float


class LLMModelUsage(BaseModel):
    model: str
    call_count: int
    prompt_tokens: int
    completion_tokens: int
    cost_cents: float


class LLMUsageSummary(BaseModel):
    total_call_count: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_cost_cents: float
    last_30d_cost_cents: float
    by_surface: list[LLMSurfaceUsage]
    by_model: list[LLMModelUsage]
