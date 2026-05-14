from __future__ import annotations

from pydantic import BaseModel


class CompanyOut(BaseModel):
    id: int
    ticker: str
    name: str
    market: str
    sector: str | None
    is_primary: bool
