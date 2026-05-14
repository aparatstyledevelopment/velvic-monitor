"""Drop all seed + backfill data, keep schema + users + orgs.

Two modes:

    python -m app.admin.reset_data                  # full reset (incl. companies)
    python -m app.admin.reset_data --keep-companies # keep company + peer rows

Always preserves: `org`, `app_user`.

Run on DO with:

    doctl apps console <app-id> --component web
    python -m app.admin.reset_data
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import text

from app.core.db import SessionLocal
from app.core.logging import logger

# Order matters only when CASCADE is not used. We use TRUNCATE ... CASCADE
# so the order is flexible; the grouping below is for readability.
TIER1_RAW = [
    "yahoo_price_bar",
    "mfn_press_release",
    "riksbank_observation",
    "scb_observation",
    "fred_observation",
    "esap_filing",
    "fi_insider_transaction",
    "fi_short_position",
    "company_ir_rss_item",
    "crawl_run",
]

TIER2_CURATED = [
    "price_bar",
    "news_item",
    "macro_observation",
]

TIER3_DERIVED = [
    "engine_call",
    "briefing_card",
    "daily_attribution",
]

CHAT_HISTORY = [
    "chat_engine_call",
    "chat_turn",
    "chat_thread",
    "llm_call_log",
]

COMPANY_TABLES = [
    "peer_relationship",
    "org_company_access",
    "company",
]


async def reset(*, keep_companies: bool) -> None:
    tables = TIER1_RAW + TIER2_CURATED + TIER3_DERIVED + CHAT_HISTORY
    if not keep_companies:
        tables = tables + COMPANY_TABLES

    quoted = ", ".join(f'"{t}"' for t in tables)
    stmt = f"TRUNCATE {quoted} RESTART IDENTITY CASCADE;"

    async with SessionLocal() as session:
        logger.info("reset_data_begin", tables=tables, keep_companies=keep_companies)
        await session.execute(text(stmt))
        await session.commit()
        logger.info("reset_data_done")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keep-companies",
        action="store_true",
        help="Keep company, peer_relationship, and org_company_access rows.",
    )
    args = parser.parse_args()
    asyncio.run(reset(keep_companies=args.keep_companies))


if __name__ == "__main__":
    main()
