"""phase-1 data model: Tier-1 raw + Tier-2 curated + Tier-3 derived + engine_call ledger

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Helper -- TIMESTAMPTZ with default now()
def _ts(server_default: bool = True) -> sa.TIMESTAMP:
    return sa.TIMESTAMP(timezone=True)


def upgrade() -> None:
    # ------------------------------------------------------------------
    # peer_relationship (Tier-2-ish; depends on company)
    # ------------------------------------------------------------------
    op.create_table(
        "peer_relationship",
        sa.Column(
            "company_id",
            sa.BigInteger(),
            sa.ForeignKey("company.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "peer_company_id",
            sa.BigInteger(),
            sa.ForeignKey("company.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("rank", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "set_at",
            _ts(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "set_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("app_user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "company_id <> peer_company_id", name="peer_relationship_no_self"
        ),
    )

    # ------------------------------------------------------------------
    # crawl_run -- operational ledger for crawlers
    # ------------------------------------------------------------------
    op.create_table(
        "crawl_run",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("crawler_name", sa.Text(), nullable=False),
        sa.Column("window_start", _ts(), nullable=True),
        sa.Column("window_end", _ts(), nullable=True),
        sa.Column(
            "started_at",
            _ts(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("finished_at", _ts(), nullable=True),
        sa.Column(
            "status", sa.Text(), nullable=False, server_default=sa.text("'running'")
        ),
        sa.Column(
            "rows_inserted",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('running','ok','failed')", name="crawl_run_status_check"
        ),
    )
    op.create_index(
        "crawl_run_recent", "crawl_run", ["crawler_name", "started_at"], unique=False
    )

    # ------------------------------------------------------------------
    # Tier 1 raw -- one table per source
    # ------------------------------------------------------------------
    op.create_table(
        "yahoo_price_bar",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("trading_date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(20, 6), nullable=True),
        sa.Column("high", sa.Numeric(20, 6), nullable=True),
        sa.Column("low", sa.Numeric(20, 6), nullable=True),
        sa.Column("close", sa.Numeric(20, 6), nullable=True),
        sa.Column("adj_close", sa.Numeric(20, 6), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("fetched_at", _ts(), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "superseded_by",
            sa.BigInteger(),
            sa.ForeignKey("yahoo_price_bar.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.execute(
        "CREATE UNIQUE INDEX yahoo_price_bar_unique "
        "ON yahoo_price_bar(ticker, trading_date) "
        "WHERE superseded_by IS NULL"
    )

    op.create_table(
        "mfn_press_release",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("mfn_id", sa.Text(), nullable=False, unique=True),
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("published_at", _ts(), nullable=False),
        sa.Column("mfn_url", sa.Text(), nullable=False),
        sa.Column("mar_flagged", sa.Boolean(), nullable=True),
        sa.Column("language", sa.Text(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("fetched_at", _ts(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "mfn_press_release_lookup",
        "mfn_press_release",
        ["ticker", "published_at"],
    )

    op.create_table(
        "riksbank_observation",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("series_id", sa.Text(), nullable=False),
        sa.Column("observation_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(20, 8), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("fetched_at", _ts(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "riksbank_observation_unique",
        "riksbank_observation",
        ["series_id", "observation_date"],
        unique=True,
    )

    op.create_table(
        "scb_observation",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("table_id", sa.Text(), nullable=False),
        sa.Column("dimensions", postgresql.JSONB(), nullable=False),
        sa.Column("observation_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(20, 8), nullable=True),
        sa.Column("unit", sa.Text(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("fetched_at", _ts(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "scb_observation_lookup", "scb_observation", ["table_id", "observation_date"]
    )

    op.create_table(
        "fred_observation",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("series_id", sa.Text(), nullable=False),
        sa.Column("observation_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(20, 8), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("fetched_at", _ts(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "fred_observation_unique",
        "fred_observation",
        ["series_id", "observation_date"],
        unique=True,
    )

    op.create_table(
        "esap_filing",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("esap_id", sa.Text(), nullable=False, unique=True),
        sa.Column("ticker", sa.Text(), nullable=True),
        sa.Column("filing_type", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("filed_at", _ts(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("fetched_at", _ts(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("esap_filing_lookup", "esap_filing", ["ticker", "filed_at"])

    op.create_table(
        "fi_insider_transaction",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("publication_id", sa.Text(), nullable=False, unique=True),
        sa.Column("issuer", sa.Text(), nullable=False),
        sa.Column("person", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=True),
        sa.Column("transaction_type", sa.Text(), nullable=False),
        sa.Column("shares", sa.Numeric(20, 4), nullable=True),
        sa.Column("price", sa.Numeric(20, 6), nullable=True),
        sa.Column("value", sa.Numeric(20, 2), nullable=True),
        sa.Column("currency", sa.Text(), nullable=True),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("fetched_at", _ts(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "fi_insider_lookup",
        "fi_insider_transaction",
        ["issuer", "transaction_date"],
    )

    op.create_table(
        "fi_short_position",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("issuer", sa.Text(), nullable=False),
        sa.Column("position_holder", sa.Text(), nullable=False),
        sa.Column("position_pct", sa.Numeric(8, 4), nullable=False),
        sa.Column("position_date", sa.Date(), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("fetched_at", _ts(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("fi_short_lookup", "fi_short_position", ["issuer", "position_date"])

    op.create_table(
        "company_ir_rss_item",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "company_id",
            sa.BigInteger(),
            sa.ForeignKey("company.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("guid", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("published_at", _ts(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("fetched_at", _ts(), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("company_id", "guid", name="company_ir_rss_item_unique"),
    )

    # ------------------------------------------------------------------
    # Tier 2 curated
    # ------------------------------------------------------------------
    op.create_table(
        "price_bar",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "company_id",
            sa.BigInteger(),
            sa.ForeignKey("company.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("trading_date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(20, 6), nullable=True),
        sa.Column("high", sa.Numeric(20, 6), nullable=True),
        sa.Column("low", sa.Numeric(20, 6), nullable=True),
        sa.Column("close", sa.Numeric(20, 6), nullable=False),
        sa.Column("adj_close", sa.Numeric(20, 6), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("source_row_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "ingested_at",
            _ts(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("company_id", "trading_date", name="price_bar_unique"),
    )
    op.create_index("price_bar_lookup", "price_bar", ["company_id", "trading_date"])

    op.create_table(
        "news_item",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "company_id",
            sa.BigInteger(),
            sa.ForeignKey("company.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("body_summary", sa.Text(), nullable=True),
        sa.Column("published_at", _ts(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("source_row_id", sa.BigInteger(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("mar_flagged", sa.Boolean(), nullable=True),
        sa.Column("language", sa.Text(), nullable=True),
        sa.Column(
            "also_seen_in",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column(
            "ingested_at",
            _ts(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("source", "source_row_id", name="news_item_unique"),
    )
    op.create_index("news_item_lookup", "news_item", ["company_id", "published_at"])
    op.execute(
        "CREATE INDEX news_item_search "
        "ON news_item USING gin(to_tsvector('simple', headline))"
    )

    op.create_table(
        "macro_observation",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("series_code", sa.Text(), nullable=False),
        sa.Column("observation_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(20, 8), nullable=False),
        sa.Column("unit", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("source_row_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "ingested_at",
            _ts(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "series_code", "observation_date", name="macro_observation_unique"
        ),
    )
    op.create_index(
        "macro_observation_lookup",
        "macro_observation",
        ["series_code", "observation_date"],
    )

    # ------------------------------------------------------------------
    # Analytics views (read-only target for ad_hoc_query)
    # ------------------------------------------------------------------
    op.execute(
        "CREATE VIEW company_v AS "
        "SELECT id, ticker, isin, name, country, market, sector, industry, "
        "       market_cap_band "
        "FROM company WHERE active = true"
    )
    op.execute(
        "CREATE VIEW price_bar_v AS "
        "SELECT company_id, trading_date, open, high, low, close, adj_close, volume "
        "FROM price_bar"
    )
    op.execute(
        "CREATE VIEW news_item_v AS "
        "SELECT id, company_id, headline, body_summary, published_at, source, "
        "       source_url, mar_flagged "
        "FROM news_item"
    )
    op.execute(
        "CREATE VIEW macro_observation_v AS "
        "SELECT series_code, observation_date, value, unit, source "
        "FROM macro_observation"
    )
    op.execute(
        "CREATE VIEW peer_relationship_v AS "
        "SELECT company_id, peer_company_id, rank FROM peer_relationship"
    )

    # ------------------------------------------------------------------
    # Tier 3 derived
    # ------------------------------------------------------------------
    op.create_table(
        "daily_attribution",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "company_id",
            sa.BigInteger(),
            sa.ForeignKey("company.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("return_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("benchmark_return_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("sector_return_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("relative_to_benchmark_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("relative_to_sector_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column(
            "computed_at",
            _ts(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("engine_version", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "company_id", "as_of_date", name="daily_attribution_unique"
        ),
    )

    op.create_table(
        "briefing_card",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "company_id",
            sa.BigInteger(),
            sa.ForeignKey("company.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("module", sa.Text(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("narrative", sa.Text(), nullable=False),
        sa.Column("smart_chips", postgresql.JSONB(), nullable=False),
        sa.Column("citation_spans", postgresql.JSONB(), nullable=False),
        sa.Column("fact_pack_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column(
            "engine_call_ids",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
        ),
        sa.Column("llm_provider", sa.Text(), nullable=False),
        sa.Column("llm_model", sa.Text(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_cents", sa.Numeric(10, 4), nullable=True),
        sa.Column(
            "generated_at",
            _ts(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "company_id", "module", "as_of_date", name="briefing_card_unique"
        ),
    )
    op.create_index(
        "briefing_card_recent",
        "briefing_card",
        ["company_id", "module", "as_of_date"],
    )

    # ------------------------------------------------------------------
    # Engine call ledger
    # ------------------------------------------------------------------
    op.create_table(
        "engine_call",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("tool_name", sa.Text(), nullable=False),
        sa.Column("module", sa.Text(), nullable=False),
        sa.Column("params", postgresql.JSONB(), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=False),
        sa.Column("source_refs", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("engine_version", sa.Text(), nullable=False),
        sa.Column(
            "called_at",
            _ts(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('ok','error','timeout')", name="engine_call_status_check"
        ),
    )
    op.create_index("engine_call_lookup", "engine_call", ["tool_name", "called_at"])

    # ------------------------------------------------------------------
    # Read-only role for ad_hoc_query
    # ------------------------------------------------------------------
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'engine_readonly') THEN
                CREATE ROLE engine_readonly NOLOGIN;
            END IF;
        END$$;
        """
    )
    op.execute(
        "GRANT SELECT ON company_v, price_bar_v, news_item_v, "
        "macro_observation_v, peer_relationship_v TO engine_readonly"
    )


def downgrade() -> None:
    op.execute(
        "REVOKE SELECT ON company_v, price_bar_v, news_item_v, "
        "macro_observation_v, peer_relationship_v FROM engine_readonly"
    )
    op.execute("DROP INDEX IF EXISTS engine_call_lookup")
    op.drop_table("engine_call")
    op.execute("DROP INDEX IF EXISTS briefing_card_recent")
    op.drop_table("briefing_card")
    op.drop_table("daily_attribution")
    op.execute("DROP VIEW IF EXISTS peer_relationship_v")
    op.execute("DROP VIEW IF EXISTS macro_observation_v")
    op.execute("DROP VIEW IF EXISTS news_item_v")
    op.execute("DROP VIEW IF EXISTS price_bar_v")
    op.execute("DROP VIEW IF EXISTS company_v")
    op.execute("DROP INDEX IF EXISTS macro_observation_lookup")
    op.drop_table("macro_observation")
    op.execute("DROP INDEX IF EXISTS news_item_search")
    op.execute("DROP INDEX IF EXISTS news_item_lookup")
    op.drop_table("news_item")
    op.execute("DROP INDEX IF EXISTS price_bar_lookup")
    op.drop_table("price_bar")
    op.drop_table("company_ir_rss_item")
    op.execute("DROP INDEX IF EXISTS fi_short_lookup")
    op.drop_table("fi_short_position")
    op.execute("DROP INDEX IF EXISTS fi_insider_lookup")
    op.drop_table("fi_insider_transaction")
    op.execute("DROP INDEX IF EXISTS esap_filing_lookup")
    op.drop_table("esap_filing")
    op.execute("DROP INDEX IF EXISTS fred_observation_unique")
    op.drop_table("fred_observation")
    op.execute("DROP INDEX IF EXISTS scb_observation_lookup")
    op.drop_table("scb_observation")
    op.execute("DROP INDEX IF EXISTS riksbank_observation_unique")
    op.drop_table("riksbank_observation")
    op.execute("DROP INDEX IF EXISTS mfn_press_release_lookup")
    op.drop_table("mfn_press_release")
    op.execute("DROP INDEX IF EXISTS yahoo_price_bar_unique")
    op.drop_table("yahoo_price_bar")
    op.execute("DROP INDEX IF EXISTS crawl_run_recent")
    op.drop_table("crawl_run")
    op.drop_table("peer_relationship")
