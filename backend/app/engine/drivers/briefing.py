"""Drivers briefing composer.

Assembles a deterministic FactPack from Engine tool results, calls the
Narrator (LLM) with the strict citation prompt, parses + validates the
response, then persists a briefing_card row. The ONLY engine code that
calls the LLM (carve-out documented in engine/AGENTS.md and ADR 0003).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import Company
from app.chat.anthropic_messages_client import call_messages
from app.chat.citations import (
    auto_ground,
    build_values_index,
    find_uncited_numerics,
    parse_citations,
)
from app.chat.llm_log import LLMCallStats, LLMLogContext, record_call
from app.core.logging import logger
from app.engine.drivers.prompts import (
    BRIEFING_SYSTEM_PROMPT,
    NEWS_SUMMARY_PROMPT,
)
from app.engine.drivers.tools import (
    get_attribution,
    get_benchmark_move,
    get_macro_snapshot,
    get_news_for_company,
    get_peer_returns,
    get_price_move,
    get_sector_proxy_return,
)
from app.engine.drivers.types import NewsSummary
from app.engine.envelope import EngineResult, SourceRef
from app.engine.models import BriefingCard
from app.engine.registry import engine_tool
from app.ingestion.models import NewsItem

# ----------------------------------------------------------------------------
# 7 -- get_press_release_summary (the LLM-bound Engine tool carve-out)
# ----------------------------------------------------------------------------


@engine_tool(
    name="get_press_release_summary",
    module="drivers",
    description=(
        "One-line summary of a press release for use in briefings and chat. "
        "Cached per news_item_id."
    ),
    cost_class="moderate",
    returns_model=NewsSummary,
)
async def get_press_release_summary(
    *, session: AsyncSession, news_item_id: int
) -> EngineResult[NewsSummary]:
    item = await session.get(NewsItem, news_item_id)
    if item is None:
        raise ValueError(f"unknown news_item_id: {news_item_id}")

    summary = item.body_summary
    if summary is None and item.body_text:
        try:
            result = await call_messages(
                system="You write tight one-line IR press-release summaries.",
                user=NEWS_SUMMARY_PROMPT.format(
                    language=item.language or "Swedish/English",
                    title=item.headline,
                    body_text=item.body_text[:4000],
                ),
                max_tokens=80,
            )
            await record_call(
                session,
                surface="news_summary",
                transport="messages_api",
                stats=LLMCallStats(
                    model=result.model,
                    prompt_tokens=result.prompt_tokens,
                    completion_tokens=result.completion_tokens,
                    cost_cents=result.cost_cents,
                ),
                ctx=LLMLogContext(company_id=item.company_id),
            )
            summary = result.text.strip().splitlines()[0][:300] if result.text else None
            if summary:
                item.body_summary = summary
                await session.flush()
        except Exception as e:
            logger.warning(
                "news_summary_failed", news_item_id=news_item_id, error=str(e)
            )
            summary = None

    return EngineResult(
        engine_call_id="pending",
        tool_name="pending",
        module="drivers",
        params={},
        data=NewsSummary(
            news_item_id=item.id,
            headline=item.headline,
            summary=summary,
            published_at=item.published_at,
            source=item.source,
            source_url=item.source_url,
            mar_flagged=item.mar_flagged,
        ),
        sources=[
            SourceRef(
                id=f"news_item_{item.id}",
                kind="news_item",
                description=item.headline[:80],
                url=item.source_url,
                row_ids=[item.id],
            )
        ],
        computed_at=datetime.now(UTC),
        engine_version="pending",
        latency_ms=0,
    )


# ----------------------------------------------------------------------------
# FactPack assembly
# ----------------------------------------------------------------------------


async def build_fact_pack(
    session: AsyncSession, *, company_id: int, as_of: date
) -> dict[str, Any]:
    pm = await get_price_move(session=session, company_id=company_id, as_of=as_of)
    bm = await get_benchmark_move(session=session, as_of=as_of)
    pr = await get_peer_returns(session=session, company_id=company_id, as_of=as_of)
    sr = await get_sector_proxy_return(
        session=session, company_id=company_id, as_of=as_of
    )
    ms = await get_macro_snapshot(session=session, as_of=as_of)
    nl = await get_news_for_company(
        session=session,
        company_id=company_id,
        start=as_of - timedelta(days=5),
        end=as_of,
    )
    attribution = await get_attribution(
        session=session, company_id=company_id, as_of=as_of
    )
    pack = {
        "company_id": company_id,
        "as_of": as_of.isoformat(),
        "price_move": _bundle(pm),
        "benchmark": _bundle(bm),
        "peer_returns": _bundle(pr),
        "sector_proxy": _bundle(sr),
        "macro_snapshot": _bundle(ms),
        "news": _bundle(nl),
        "attribution": _bundle(attribution),
    }
    return pack


def _bundle(result: EngineResult[Any]) -> dict[str, Any]:
    data = result.data.model_dump(mode="json")
    if isinstance(data, dict):
        data["_engine_call_id"] = result.engine_call_id
    return {
        "engine_call_id": result.engine_call_id,
        "data": data,
    }


_FACT_PACK_SECTIONS = (
    "price_move",
    "benchmark",
    "peer_returns",
    "sector_proxy",
    "macro_snapshot",
    "news",
    "attribution",
)


def fact_pack_engine_call_ids(pack: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for key in _FACT_PACK_SECTIONS:
        ec_id = pack.get(key, {}).get("engine_call_id")
        if isinstance(ec_id, str) and ec_id.startswith("ec_"):
            ids.append(ec_id)
    return ids


def fact_pack_values_index(pack: dict[str, Any]) -> dict[str, set[str]]:
    sources: list[tuple[str, Any]] = []
    for key in _FACT_PACK_SECTIONS:
        section = pack.get(key)
        if not isinstance(section, dict):
            continue
        ec_id = section.get("engine_call_id")
        if not isinstance(ec_id, str) or not ec_id.startswith("ec_"):
            continue
        sources.append((ec_id, section.get("data")))
    return build_values_index(sources)


# ----------------------------------------------------------------------------
# Briefing generation
# ----------------------------------------------------------------------------


async def generate_briefing(
    session: AsyncSession,
    *,
    company_id: int,
    as_of: date,
    model: str | None = None,
) -> BriefingCard:
    company = await session.get(Company, company_id)
    if company is None:
        raise ValueError(f"unknown company_id: {company_id}")

    pack = await build_fact_pack(session, company_id=company_id, as_of=as_of)
    valid_ids = set(fact_pack_engine_call_ids(pack))
    values_index = fact_pack_values_index(pack)

    user_prompt = (
        f"Company: {company.name} ({company.ticker})\n"
        f"As-of: {as_of.isoformat()}\n\n"
        f"FactPack:\n{json.dumps(pack, indent=2, default=_jsonable_default)}\n"
    )

    response = await call_messages(
        system=BRIEFING_SYSTEM_PROMPT,
        user=user_prompt,
        max_tokens=1500,
        model=model,
    )
    await record_call(
        session,
        surface="briefing_narrative",
        transport="messages_api",
        stats=LLMCallStats(
            model=response.model,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            cost_cents=response.cost_cents,
        ),
        ctx=LLMLogContext(company_id=company_id),
    )
    parsed = _parse_briefing_response(response.text, valid_ids, values_index)

    if parsed.has_uncited_numerics:
        logger.warning(
            "briefing_uncited_numerics",
            company_id=company_id,
            as_of=as_of.isoformat(),
            count=len(parsed.uncited),
        )

    existing = await session.scalar(
        select(BriefingCard).where(
            BriefingCard.company_id == company_id,
            BriefingCard.module == "drivers",
            BriefingCard.as_of_date == as_of,
        )
    )
    if existing is not None:
        existing.narrative = parsed.narrative
        existing.smart_chips = parsed.smart_chips
        existing.citation_spans = [s.__dict__ for s in parsed.spans]
        existing.fact_pack_snapshot = pack
        existing.engine_call_ids = list(valid_ids)
        existing.llm_provider = "anthropic"
        existing.llm_model = response.model
        existing.prompt_tokens = response.prompt_tokens
        existing.completion_tokens = response.completion_tokens
        existing.cost_cents = Decimal(str(response.cost_cents))
        await session.flush()
        return existing

    row = BriefingCard(
        company_id=company_id,
        module="drivers",
        as_of_date=as_of,
        narrative=parsed.narrative,
        smart_chips=parsed.smart_chips,
        citation_spans=[s.__dict__ for s in parsed.spans],
        fact_pack_snapshot=pack,
        engine_call_ids=list(valid_ids),
        llm_provider="anthropic",
        llm_model=response.model,
        prompt_tokens=response.prompt_tokens,
        completion_tokens=response.completion_tokens,
        cost_cents=Decimal(str(response.cost_cents)),
    )
    session.add(row)
    await session.flush()
    return row


# ----------------------------------------------------------------------------
# Response parsing
# ----------------------------------------------------------------------------


@dataclass(frozen=True)
class ParsedBriefing:
    narrative: str
    smart_chips: list[dict[str, str]]  # [{"title": ..., "prompt": ...}]
    spans: list[Any]
    has_uncited_numerics: bool
    uncited: list[tuple[int, int, str]]


def _parse_briefing_response(
    raw: str,
    valid_ids: set[str],
    values_index: dict[str, set[str]] | None = None,
) -> ParsedBriefing:
    payload = _extract_json(raw)
    narrative_raw = payload.get("narrative") or ""
    chips = _normalise_smart_chips(payload.get("smart_chips"))

    parsed = parse_citations(narrative_raw, valid_ids)
    if values_index:
        parsed = auto_ground(parsed, values_index, valid_ids)
    uncited = find_uncited_numerics(parsed.text, parsed.spans)
    return ParsedBriefing(
        narrative=parsed.text,
        smart_chips=chips,
        spans=parsed.spans,
        has_uncited_numerics=bool(uncited),
        uncited=uncited,
    )


def _normalise_smart_chips(raw: Any) -> list[dict[str, str]]:
    """Accept either the new {title, prompt} shape or a list of raw prompt strings.

    Strings are upgraded into chips by deriving a <=4-word title from the
    prompt itself; this keeps legacy briefing rows renderable while we
    migrate to the explicit-title shape.
    """
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw[:5]:
        if isinstance(item, dict):
            title = str(item.get("title", "")).strip()
            prompt = str(item.get("prompt", "")).strip()
            if not prompt and title:
                prompt = title
            if not title and prompt:
                title = _derive_short_title(prompt)
            if title and prompt:
                out.append(
                    {"title": _trim_words(title, 4), "prompt": prompt}
                )
        elif isinstance(item, str):
            prompt = item.strip()
            if prompt:
                out.append(
                    {"title": _derive_short_title(prompt), "prompt": prompt}
                )
    return out


def _trim_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


_LEAD_INTERROGATIVES = (
    "what is ", "what are ", "what's ", "what ",
    "why ", "how ", "who ", "any ", "show me ",
    "tell me ", "compare ", "list ", "find ",
)


def _derive_short_title(prompt: str) -> str:
    body = prompt.strip().rstrip("?.!,;:")
    lower = body.lower()
    for lead in _LEAD_INTERROGATIVES:
        if lower.startswith(lead):
            body = body[len(lead) :]
            break
    body = body.strip()
    if not body:
        body = prompt.strip().rstrip("?.!,;:")
    body = body[:1].upper() + body[1:]
    return _trim_words(body, 4)


def _extract_json(s: str) -> dict[str, Any]:
    """LLMs sometimes wrap JSON in code fences; strip them and parse."""
    s = s.strip()
    if s.startswith("```"):
        s = s.strip("`")
        first_nl = s.find("\n")
        if first_nl != -1:
            s = s[first_nl + 1 :]
    try:
        parsed: dict[str, Any] = json.loads(s)
        return parsed
    except json.JSONDecodeError:
        return {"narrative": s, "smart_chips": []}


def _jsonable_default(o: Any) -> Any:
    if isinstance(o, Decimal):
        return float(o)
    if hasattr(o, "isoformat"):
        return o.isoformat()
    return str(o)
