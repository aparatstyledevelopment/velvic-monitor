"""Drivers-module data endpoints.

Two surfaces:

- `GET /api/companies/{company_id}/snapshot` — top-bar identity + latest
  price/return, sourced from the latest briefing's fact_pack_snapshot so
  no fresh Engine work is required and provenance carries over via the
  cited engine_call_id.

- `GET /api/companies/{company_id}/drivers/data/{source}` — one slice of
  the same fact_pack_snapshot, exposed as the &ldquo;ground truth&rdquo; surfaces
  the Quick Actions panel drills into. Five sources are supported:
  price_action, comparators, news_flow, macro, attribution.

Both endpoints serve already-computed data. They never trigger fresh
Engine calls; they read what the daily briefing pipeline cached.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.drivers import CompanySnapshotOut, DriversDataOut
from app.auth.deps import current_user
from app.auth.models import AppUser, Company, OrgCompanyAccess
from app.core.db import get_session
from app.core.errors import NotFoundError, to_http
from app.engine.models import BriefingCard

router = APIRouter(prefix="/companies", tags=["drivers"])


_SOURCE_DEFINITIONS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    # source key → (label, description, fact_pack keys to expose)
    "price_action": (
        "Price action",
        "Today's price, return, and reference levels.",
        ("price_move",),
    ),
    "comparators": (
        "Comparators",
        "Benchmark, sector proxy, and peer returns alongside today's move.",
        ("benchmark", "sector_proxy", "peer_returns"),
    ),
    "news_flow": (
        "News flow",
        "Regulatory and IR news touching this name in the last five days.",
        ("news",),
    ),
    "macro": (
        "Macro context",
        "Today's FX, rate, and central-bank macro snapshot.",
        ("macro_snapshot",),
    ),
    "attribution": (
        "Daily attribution",
        "Computed return decomposition vs benchmark and sector.",
        ("attribution",),
    ),
}


async def _ensure_access(
    session: AsyncSession, *, user: AppUser, company_id: int
) -> Company:
    access = await session.scalar(
        select(OrgCompanyAccess).where(
            OrgCompanyAccess.org_id == user.org_id,
            OrgCompanyAccess.company_id == company_id,
        )
    )
    if access is None:
        raise to_http(NotFoundError("company not in scope for org"))
    company = await session.get(Company, company_id)
    if company is None:
        raise to_http(NotFoundError("company not found"))
    return company


async def _latest_briefing(
    session: AsyncSession, *, company_id: int
) -> BriefingCard | None:
    row: BriefingCard | None = await session.scalar(
        select(BriefingCard)
        .where(BriefingCard.company_id == company_id, BriefingCard.module == "drivers")
        .order_by(desc(BriefingCard.as_of_date))
        .limit(1)
    )
    return row


def _safe_get(d: Any, *keys: str) -> Any:
    cursor: Any = d
    for k in keys:
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(k)
    return cursor


@router.get(
    "/{company_id}/snapshot",
    response_model=CompanySnapshotOut,
    status_code=status.HTTP_200_OK,
)
async def company_snapshot(
    company_id: int,
    user: AppUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> CompanySnapshotOut:
    company = await _ensure_access(session, user=user, company_id=company_id)
    briefing = await _latest_briefing(session, company_id=company_id)
    if briefing is None:
        return CompanySnapshotOut(
            company_id=company.id,
            ticker=company.ticker,
            name=company.name,
            market=company.market,
            sector=company.sector,
            as_of_date=None,
            price=None,
            return_pct=None,
            price_engine_call_id=None,
        )

    pack = briefing.fact_pack_snapshot
    price_block = pack.get("price_move", {}) if isinstance(pack, dict) else {}
    data = price_block.get("data", {}) if isinstance(price_block, dict) else {}
    price = _safe_get(data, "close")
    return_pct = _safe_get(data, "return_pct")

    return CompanySnapshotOut(
        company_id=company.id,
        ticker=company.ticker,
        name=company.name,
        market=company.market,
        sector=company.sector,
        as_of_date=briefing.as_of_date,
        price=float(price) if isinstance(price, int | float) else None,
        return_pct=(float(return_pct) if isinstance(return_pct, int | float) else None),
        price_engine_call_id=(
            price_block.get("engine_call_id") if isinstance(price_block, dict) else None
        ),
    )


@router.get(
    "/{company_id}/drivers/data/{source}",
    response_model=DriversDataOut,
    status_code=status.HTTP_200_OK,
)
async def drivers_data(
    company_id: int,
    source: str,
    user: AppUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> DriversDataOut:
    if source not in _SOURCE_DEFINITIONS:
        raise to_http(NotFoundError(f"unknown drivers source: {source}"))
    await _ensure_access(session, user=user, company_id=company_id)
    briefing = await _latest_briefing(session, company_id=company_id)
    if briefing is None:
        raise to_http(NotFoundError("no briefing yet for this company"))

    label, description, keys = _SOURCE_DEFINITIONS[source]
    pack = (
        briefing.fact_pack_snapshot
        if isinstance(briefing.fact_pack_snapshot, dict)
        else {}
    )

    sliced: dict[str, Any] = {}
    engine_call_ids: list[str] = []
    for key in keys:
        block = pack.get(key)
        if not isinstance(block, dict):
            continue
        sliced[key] = block.get("data", {})
        ec_id = block.get("engine_call_id")
        if isinstance(ec_id, str) and ec_id.startswith("ec_"):
            engine_call_ids.append(ec_id)

    return DriversDataOut(
        company_id=company_id,
        as_of_date=briefing.as_of_date,
        source=source,
        label=label,
        description=description,
        engine_call_ids=engine_call_ids,
        data=sliced,
    )
