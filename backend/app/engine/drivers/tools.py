"""Drivers module Engine tools.

Ten tools, all returning EngineResult. Reads only Tier-2 / Tier-3 (the
hard rule). The decorator wires content-addressed caching + ledger
persistence; tool bodies focus on the calculation.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import Company
from app.engine.drivers.types import (
    BenchmarkMove,
    CompanyMeta,
    DailyAttributionOut,
    MacroSeriesValue,
    MacroSnapshot,
    NewsList,
    NewsSummary,
    PeerReturn,
    PeerReturns,
    PriceBarOut,
    PriceMove,
    SectorReturn,
)
from app.engine.envelope import EngineResult, SourceRef
from app.engine.models import DailyAttribution
from app.engine.registry import engine_tool
from app.engine.shared import macro as shared_macro
from app.engine.shared import peers as shared_peers
from app.engine.shared import prices as shared_prices
from app.ingestion.models import NewsItem


BENCHMARK_TICKER = "^OMXSPI"
BENCHMARK_LABEL = "OMX Stockholm PI"


def _envelope(*, data: Any, sources: list[SourceRef]) -> EngineResult[Any]:
    """Bare envelope with placeholder fields; the decorator fills runtime fields."""
    return EngineResult(
        engine_call_id="pending",
        tool_name="pending",
        module="drivers",
        params={},
        data=data,
        sources=sources,
        computed_at=datetime.now(UTC),
        engine_version="pending",
        latency_ms=0,
    )


# ---------------------------------------------------------------------- 1


@engine_tool(
    name="get_price_move",
    module="drivers",
    description=(
        "Most recent daily price move for a Swedish-listed company "
        "(typically yesterday's close vs the prior close), with five trading "
        "days of trailing history. Use whenever the user asks how a stock "
        "moved on a given date or recent window."
    ),
    cost_class="cheap",
)
async def get_price_move(
    *, session: AsyncSession, company_id: int, as_of: date
) -> EngineResult[PriceMove]:
    company = await session.get(Company, company_id)
    if company is None:
        raise ValueError(f"unknown company_id: {company_id}")
    last = await shared_prices.latest_close_on_or_before(
        session, company_id=company_id, as_of=as_of
    )
    if last is None:
        return _envelope(
            data=PriceMove(
                ticker=company.ticker,
                company_id=company_id,
                last_close_date=as_of,
                last_close=Decimal("0"),
                prior_close_date=None,
                prior_close=None,
                daily_return_pct=None,
            ),
            sources=[],
        )
    prior = await shared_prices.prior_close(
        session, company_id=company_id, before=last.trading_date
    )
    history = await shared_prices.trailing_bars(
        session, company_id=company_id, as_of=last.trading_date, days=5
    )

    daily_return = (
        shared_prices.daily_return_pct(last.close, prior.close) if prior is not None else None
    )

    sources = [
        SourceRef(
            id=f"price_bar_{company_id}_{last.trading_date.isoformat()}",
            kind="price_bar",
            description=f"Tier-2 price_bar row for {company.ticker} on {last.trading_date}",
            row_ids=[last.id],
        )
    ]
    if prior is not None:
        sources.append(
            SourceRef(
                id=f"price_bar_{company_id}_{prior.trading_date.isoformat()}",
                kind="price_bar",
                description=f"Tier-2 price_bar row for {company.ticker} on {prior.trading_date}",
                row_ids=[prior.id],
            )
        )

    return _envelope(
        data=PriceMove(
            ticker=company.ticker,
            company_id=company_id,
            last_close_date=last.trading_date,
            last_close=last.close,
            prior_close_date=prior.trading_date if prior else None,
            prior_close=prior.close if prior else None,
            daily_return_pct=daily_return,
            five_day_history=[
                PriceBarOut(
                    trading_date=h.trading_date,
                    open=h.open,
                    high=h.high,
                    low=h.low,
                    close=h.close,
                    volume=h.volume,
                )
                for h in history
            ],
        ),
        sources=sources,
    )


# ---------------------------------------------------------------------- 2


@engine_tool(
    name="get_benchmark_move",
    module="drivers",
    description=(
        "Daily return for the OMX Stockholm PI broad-market index on a given "
        "date. Use to contextualize a single-stock move against the market."
    ),
    cost_class="cheap",
)
async def get_benchmark_move(
    *, session: AsyncSession, as_of: date
) -> EngineResult[BenchmarkMove]:
    benchmark = await session.scalar(
        select(Company).where(Company.yahoo_symbol == BENCHMARK_TICKER)
    )
    if benchmark is None:
        return _envelope(
            data=BenchmarkMove(
                benchmark=BENCHMARK_LABEL,
                as_of=as_of,
                last_close=Decimal("0"),
                prior_close=None,
                daily_return_pct=None,
            ),
            sources=[],
        )
    last = await shared_prices.latest_close_on_or_before(
        session, company_id=benchmark.id, as_of=as_of
    )
    if last is None:
        return _envelope(
            data=BenchmarkMove(
                benchmark=BENCHMARK_LABEL,
                as_of=as_of,
                last_close=Decimal("0"),
                prior_close=None,
                daily_return_pct=None,
            ),
            sources=[],
        )
    prior = await shared_prices.prior_close(
        session, company_id=benchmark.id, before=last.trading_date
    )
    daily_return = (
        shared_prices.daily_return_pct(last.close, prior.close) if prior is not None else None
    )
    sources = [
        SourceRef(
            id=f"benchmark_{last.trading_date.isoformat()}",
            kind="benchmark_bar",
            description=f"OMX Stockholm PI close on {last.trading_date}",
            row_ids=[last.id],
        )
    ]
    return _envelope(
        data=BenchmarkMove(
            benchmark=BENCHMARK_LABEL,
            as_of=last.trading_date,
            last_close=last.close,
            prior_close=prior.close if prior else None,
            daily_return_pct=daily_return,
        ),
        sources=sources,
    )


# ---------------------------------------------------------------------- 3


@engine_tool(
    name="get_peer_returns",
    module="drivers",
    description=(
        "Daily returns for a company's curated peer set on a given date. "
        "Use when comparing a single-stock move against industry comparables."
    ),
    cost_class="cheap",
)
async def get_peer_returns(
    *, session: AsyncSession, company_id: int, as_of: date
) -> EngineResult[PeerReturns]:
    peers = await shared_peers.peers_for_company(session, company_id)
    out: list[PeerReturn] = []
    sources: list[SourceRef] = []
    for peer in peers:
        last = await shared_prices.latest_close_on_or_before(
            session, company_id=peer.id, as_of=as_of
        )
        if last is None:
            out.append(PeerReturn(company_id=peer.id, ticker=peer.ticker, name=peer.name, daily_return_pct=None))
            continue
        prior = await shared_prices.prior_close(
            session, company_id=peer.id, before=last.trading_date
        )
        ret = (
            shared_prices.daily_return_pct(last.close, prior.close)
            if prior is not None
            else None
        )
        out.append(
            PeerReturn(company_id=peer.id, ticker=peer.ticker, name=peer.name, daily_return_pct=ret)
        )
        sources.append(
            SourceRef(
                id=f"peer_{peer.id}_{last.trading_date.isoformat()}",
                kind="price_bar",
                description=f"Peer {peer.ticker} close on {last.trading_date}",
                row_ids=[last.id],
            )
        )
    return _envelope(
        data=PeerReturns(company_id=company_id, as_of=as_of, peers=out),
        sources=sources,
    )


# ---------------------------------------------------------------------- 4


@engine_tool(
    name="get_sector_proxy_return",
    module="drivers",
    description=(
        "Sector return on a given date. Uses the sector index when available "
        "or a simple peer-average fallback. Surfaces which proxy was used."
    ),
    cost_class="cheap",
)
async def get_sector_proxy_return(
    *, session: AsyncSession, company_id: int, as_of: date
) -> EngineResult[SectorReturn]:
    company = await session.get(Company, company_id)
    if company is None:
        raise ValueError(f"unknown company_id: {company_id}")
    peers = await shared_peers.peers_for_company(session, company_id)
    if not peers:
        return _envelope(
            data=SectorReturn(
                company_id=company_id,
                sector=company.sector,
                as_of=as_of,
                daily_return_pct=None,
                proxy="unavailable",
            ),
            sources=[],
        )
    rets: list[Decimal] = []
    sources: list[SourceRef] = []
    for peer in peers:
        last = await shared_prices.latest_close_on_or_before(
            session, company_id=peer.id, as_of=as_of
        )
        if last is None:
            continue
        prior = await shared_prices.prior_close(
            session, company_id=peer.id, before=last.trading_date
        )
        if prior is None:
            continue
        rets.append(shared_prices.daily_return_pct(last.close, prior.close))
        sources.append(
            SourceRef(
                id=f"sector_proxy_{peer.id}_{last.trading_date.isoformat()}",
                kind="price_bar",
                description=f"Peer {peer.ticker} close on {last.trading_date}",
                row_ids=[last.id],
            )
        )
    avg = sum(rets) / Decimal(len(rets)) if rets else None
    return _envelope(
        data=SectorReturn(
            company_id=company_id,
            sector=company.sector,
            as_of=as_of,
            daily_return_pct=avg,
            proxy="peer_average" if rets else "unavailable",
        ),
        sources=sources,
    )


# ---------------------------------------------------------------------- 5


@engine_tool(
    name="get_macro_snapshot",
    module="drivers",
    description=(
        "Macro snapshot for a given date: SE policy rate, SEK/EUR, SEK/USD, "
        "10Y govt yield, Brent crude. Use to characterize macro context "
        "around a stock move."
    ),
    cost_class="cheap",
)
async def get_macro_snapshot(
    *, session: AsyncSession, as_of: date
) -> EngineResult[MacroSnapshot]:
    series_codes = [
        "SE.POLICY_RATE",
        "SE.SEK_PER_EUR",
        "SE.SEK_PER_USD",
        "SE.GOVT_10Y_YIELD",
        "WORLD.OIL_BRENT",
    ]
    rows: list[MacroSeriesValue] = []
    sources: list[SourceRef] = []
    for code in series_codes:
        obs = await shared_macro.latest_value_on_or_before(
            session, series_code=code, as_of=as_of
        )
        if obs is None:
            continue
        rows.append(
            MacroSeriesValue(
                series_code=code,
                observation_date=obs.observation_date,
                value=obs.value,
                unit=obs.unit,
                source=obs.source,
            )
        )
        sources.append(
            SourceRef(
                id=f"macro_{code}_{obs.observation_date.isoformat()}",
                kind="macro_observation",
                description=f"{code} on {obs.observation_date} from {obs.source}",
                row_ids=[obs.id],
            )
        )
    return _envelope(
        data=MacroSnapshot(as_of=as_of, series=rows),
        sources=sources,
    )


# ---------------------------------------------------------------------- 6


@engine_tool(
    name="get_news_for_company",
    module="drivers",
    description=(
        "News and regulatory disclosures for a company over a date window. "
        "MAR-flagged items first, then chronological. Capped at 10 items."
    ),
    cost_class="cheap",
)
async def get_news_for_company(
    *,
    session: AsyncSession,
    company_id: int,
    start: date,
    end: date,
    source_filter: str | None = None,
) -> EngineResult[NewsList]:
    stmt = (
        select(NewsItem)
        .where(NewsItem.company_id == company_id)
        .where(NewsItem.published_at >= datetime.combine(start, datetime.min.time()))
        .where(NewsItem.published_at <= datetime.combine(end, datetime.max.time()))
    )
    if source_filter is not None:
        stmt = stmt.where(NewsItem.source == source_filter)
    stmt = stmt.order_by(
        desc(NewsItem.mar_flagged.is_(True)), desc(NewsItem.published_at)
    ).limit(10)
    rows = (await session.execute(stmt)).scalars().all()
    items = [
        NewsSummary(
            news_item_id=r.id,
            headline=r.headline,
            summary=r.body_summary,
            published_at=r.published_at,
            source=r.source,
            source_url=r.source_url,
            mar_flagged=r.mar_flagged,
        )
        for r in rows
    ]
    sources = [
        SourceRef(
            id=f"news_item_{r.id}",
            kind="news_item",
            description=f"{r.source} -- {r.headline[:80]}",
            url=r.source_url,
            row_ids=[r.id],
        )
        for r in rows
    ]
    return _envelope(
        data=NewsList(company_id=company_id, start=start, end=end, items=items),
        sources=sources,
    )


# ---------------------------------------------------------------------- 7
# get_press_release_summary lives in the briefing module since it is the
# only Engine code that touches the LLM (cheap-tier summary). Defined in
# engine/drivers/briefing.py to keep the LLM-bound carve-out localized.


# ---------------------------------------------------------------------- 8


@engine_tool(
    name="get_company_meta",
    module="shared",
    description=(
        "Company metadata: ticker, name, sector, market cap band, ISIN. "
        "Use whenever the answer needs a company's basic identity."
    ),
    cost_class="cheap",
)
async def get_company_meta(
    *, session: AsyncSession, company_id: int
) -> EngineResult[CompanyMeta]:
    c = await session.get(Company, company_id)
    if c is None:
        raise ValueError(f"unknown company_id: {company_id}")
    return _envelope(
        data=CompanyMeta(
            company_id=c.id,
            ticker=c.ticker,
            isin=c.isin,
            name=c.name,
            market=c.market,
            sector=c.sector,
            industry=c.industry,
            market_cap_band=c.market_cap_band,
        ),
        sources=[
            SourceRef(
                id=f"company_{c.id}",
                kind="company",
                description=f"company row for {c.ticker}",
                row_ids=[c.id],
            )
        ],
    )


# ---------------------------------------------------------------------- 9


@engine_tool(
    name="get_attribution",
    module="drivers",
    description=(
        "Daily attribution row from Tier-3 derived: return, vs benchmark, "
        "vs sector. Returns null fields if attribution has not been "
        "computed yet for the date."
    ),
    cost_class="cheap",
)
async def get_attribution(
    *, session: AsyncSession, company_id: int, as_of: date
) -> EngineResult[DailyAttributionOut]:
    row = await session.scalar(
        select(DailyAttribution).where(
            DailyAttribution.company_id == company_id,
            DailyAttribution.as_of_date == as_of,
        )
    )
    if row is None:
        return _envelope(
            data=DailyAttributionOut(
                company_id=company_id,
                as_of_date=as_of,
                return_pct=None,
                benchmark_return_pct=None,
                sector_return_pct=None,
                relative_to_benchmark_pct=None,
                relative_to_sector_pct=None,
            ),
            sources=[],
        )
    return _envelope(
        data=DailyAttributionOut(
            company_id=company_id,
            as_of_date=as_of,
            return_pct=row.return_pct,
            benchmark_return_pct=row.benchmark_return_pct,
            sector_return_pct=row.sector_return_pct,
            relative_to_benchmark_pct=row.relative_to_benchmark_pct,
            relative_to_sector_pct=row.relative_to_sector_pct,
        ),
        sources=[
            SourceRef(
                id=f"attribution_{company_id}_{as_of.isoformat()}",
                kind="daily_attribution",
                description=f"Tier-3 daily_attribution for company={company_id} on {as_of}",
                row_ids=[row.id],
            )
        ],
    )


_ = timedelta  # silence unused import warning; kept for future helpers
