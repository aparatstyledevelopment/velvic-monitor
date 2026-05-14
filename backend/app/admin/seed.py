"""Demo seed: a popular Swedish company + its real Stockholm-listed peers.

Cohort: the four large Nordic banks. SEB is the headline; Swedbank,
Handelsbanken, and Nordea are direct competitors with strong IR
disclosure, aligned earnings cycles, and tight peer correlation —
exactly the shape the Drivers module is meant to attribute.

Run via `python -m app.admin.seed`. Idempotent.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from sqlalchemy import select

from app.auth.models import Company, PeerRelationship
from app.core.db import SessionLocal
from app.ingestion.companies import upsert_company


@dataclass(frozen=True)
class _Seed:
    ticker: str
    name: str
    yahoo_symbol: str
    market: str
    sector: str
    industry: str
    market_cap_band: str
    isin: str
    mfn_slug: str | None = None


SEED: list[_Seed] = [
    _Seed(
        ticker="SEB-A",
        name="Skandinaviska Enskilda Banken (A)",
        yahoo_symbol="SEB-A.ST",
        market="XSTO",
        sector="Financials",
        industry="Diversified Banks",
        market_cap_band="large",
        isin="SE0000148884",
        mfn_slug="seb",
    ),
    _Seed(
        ticker="SWED-A",
        name="Swedbank (A)",
        yahoo_symbol="SWED-A.ST",
        market="XSTO",
        sector="Financials",
        industry="Diversified Banks",
        market_cap_band="large",
        isin="SE0000242455",
        mfn_slug="swedbank",
    ),
    _Seed(
        ticker="SHB-A",
        name="Svenska Handelsbanken (A)",
        yahoo_symbol="SHB-A.ST",
        market="XSTO",
        sector="Financials",
        industry="Diversified Banks",
        market_cap_band="large",
        isin="SE0007100599",
        mfn_slug="handelsbanken",
    ),
    _Seed(
        ticker="NDA-SE",
        name="Nordea Bank Abp",
        yahoo_symbol="NDA-SE.ST",
        market="XSTO",
        sector="Financials",
        industry="Diversified Banks",
        market_cap_band="large",
        isin="FI4000297767",
        mfn_slug="nordea",
    ),
]

# OMX Stockholm PI is a benchmark, not a tradeable peer; we still register
# it as a Company so price_bar_v / get_benchmark_move can read it.
BENCHMARK = _Seed(
    ticker="^OMXSPI",
    name="OMX Stockholm PI",
    yahoo_symbol="^OMXSPI",
    market="XSTO",
    sector="Index",
    industry="Index",
    market_cap_band="large",
    isin="",
)


async def seed_demo_data() -> None:
    async with SessionLocal() as session:
        rows: dict[str, Company] = {}
        for s in [BENCHMARK, *SEED]:
            company = await upsert_company(
                session,
                ticker=s.ticker,
                name=s.name,
                yahoo_symbol=s.yahoo_symbol,
                market=s.market,
                sector=s.sector,
                industry=s.industry,
                market_cap_band=s.market_cap_band,
                isin=s.isin or None,
                mfn_slug=s.mfn_slug,
            )
            rows[s.ticker] = company

        # Banks cohort — every seeded ticker is a direct competitor of
        # every other. Rank is just order-of-listing; the Drivers module
        # treats all four as a single peer group.
        bank_tickers = [s.ticker for s in SEED]
        for primary in bank_tickers:
            primary_id = rows[primary].id
            others = [t for t in bank_tickers if t != primary]
            for rank, peer_t in enumerate(others):
                peer_id = rows[peer_t].id
                exists = await session.scalar(
                    select(PeerRelationship).where(
                        PeerRelationship.company_id == primary_id,
                        PeerRelationship.peer_company_id == peer_id,
                    )
                )
                if exists is not None:
                    continue
                session.add(
                    PeerRelationship(
                        company_id=primary_id,
                        peer_company_id=peer_id,
                        rank=rank,
                    )
                )

        await session.commit()
        print(
            f"seeded {len(SEED)} demo tickers "
            f"+ {len(SEED) * (len(bank_tickers) - 1)} peer rows "
            f"(Nordic banks cohort)"
        )


def main() -> None:
    asyncio.run(seed_demo_data())


if __name__ == "__main__":
    main()
