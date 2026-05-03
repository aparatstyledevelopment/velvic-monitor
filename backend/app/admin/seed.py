"""Demo seed: five Swedish blue-chips with peer relationships.

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
        ticker="VOLV-B",
        name="AB Volvo (B)",
        yahoo_symbol="VOLV-B.ST",
        market="XSTO",
        sector="Industrials",
        industry="Heavy Trucks",
        market_cap_band="large",
        isin="SE0000115446",
        mfn_slug="volvo",
    ),
    _Seed(
        ticker="ATCO-A",
        name="Atlas Copco (A)",
        yahoo_symbol="ATCO-A.ST",
        market="XSTO",
        sector="Industrials",
        industry="Industrial Machinery",
        market_cap_band="large",
        isin="SE0011166610",
        mfn_slug="atlas-copco",
    ),
    _Seed(
        ticker="SAND",
        name="Sandvik AB",
        yahoo_symbol="SAND.ST",
        market="XSTO",
        sector="Industrials",
        industry="Industrial Machinery",
        market_cap_band="large",
        isin="SE0000667891",
        mfn_slug="sandvik",
    ),
    _Seed(
        ticker="SKF-B",
        name="AB SKF (B)",
        yahoo_symbol="SKF-B.ST",
        market="XSTO",
        sector="Industrials",
        industry="Industrial Machinery",
        market_cap_band="large",
        isin="SE0000108227",
        mfn_slug="skf",
    ),
    _Seed(
        ticker="ERIC-B",
        name="Telefonaktiebolaget LM Ericsson (B)",
        yahoo_symbol="ERIC-B.ST",
        market="XSTO",
        sector="Communication Services",
        industry="Communications Equipment",
        market_cap_band="large",
        isin="SE0000108656",
        mfn_slug="ericsson",
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
        # Upsert companies
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

        # Industrials peer set: VOLV-B / ATCO-A / SAND / SKF-B (order by market cap intuition)
        industrials = ["VOLV-B", "ATCO-A", "SAND", "SKF-B"]
        for primary in industrials:
            primary_id = rows[primary].id
            others = [t for t in industrials if t != primary]
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
            f"seeded {len(SEED)} demo tickers + {len(SEED) * (len(industrials) - 1)} peer rows (industrials cohort)"
        )


def main() -> None:
    asyncio.run(seed_demo_data())


if __name__ == "__main__":
    main()
