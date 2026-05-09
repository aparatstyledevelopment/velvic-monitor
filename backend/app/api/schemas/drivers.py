from __future__ import annotations

from datetime import date as Date
from typing import Any

from pydantic import BaseModel


class CompanySnapshotOut(BaseModel):
    """Top-bar payload: identity + latest price/return + provenance."""

    company_id: int
    ticker: str
    name: str
    market: str
    sector: str | None
    as_of_date: Date | None
    price: float | None
    return_pct: float | None
    price_engine_call_id: str | None


class DriversDataOut(BaseModel):
    """One slice of the latest fact-pack snapshot (Drivers ground truth)."""

    company_id: int
    as_of_date: Date
    source: str
    label: str
    description: str
    engine_call_ids: list[str]
    data: dict[str, Any]
