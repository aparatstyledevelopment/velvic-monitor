"""Company onboarding helpers (admin path).

Phase-1 surface: a minimal `upsert_company` used by the demo seeder and
the admin onboarding flow that arrives in Phase 4.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import Company


async def upsert_company(
    session: AsyncSession,
    *,
    ticker: str,
    name: str,
    yahoo_symbol: str,
    market: str,
    isin: str | None = None,
    sector: str | None = None,
    industry: str | None = None,
    market_cap_band: str | None = None,
    mfn_slug: str | None = None,
    ir_rss_url: str | None = None,
) -> Company:
    company = await session.scalar(select(Company).where(Company.ticker == ticker))
    if company is None:
        company = Company(
            ticker=ticker,
            name=name,
            yahoo_symbol=yahoo_symbol,
            market=market,
            isin=isin,
            sector=sector,
            industry=industry,
            market_cap_band=market_cap_band,
            mfn_slug=mfn_slug,
            ir_rss_url=ir_rss_url,
        )
        session.add(company)
        await session.flush()
        return company

    company.name = name
    company.yahoo_symbol = yahoo_symbol
    company.market = market
    if isin is not None:
        company.isin = isin
    if sector is not None:
        company.sector = sector
    if industry is not None:
        company.industry = industry
    if market_cap_band is not None:
        company.market_cap_band = market_cap_band
    if mfn_slug is not None:
        company.mfn_slug = mfn_slug
    if ir_rss_url is not None:
        company.ir_rss_url = ir_rss_url
    await session.flush()
    return company
