"""initial schema: org, app_user, company, org_company_access

Revision ID: 0001
Revises:
Create Date: 2026-04-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "org",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("plan", sa.Text(), nullable=False, server_default=sa.text("'pilot'")),
        sa.Column(
            "llm_provider_pref",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'anthropic'"),
        ),
        sa.Column("llm_api_key_enc", postgresql.BYTEA(), nullable=True),
        sa.Column(
            "monthly_token_budget",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("1000000"),
        ),
        sa.Column(
            "monthly_tokens_used",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("billing_email", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "llm_provider_pref IN ('anthropic','openai','google')",
            name="org_llm_provider_pref_check",
        ),
    )

    op.create_table(
        "app_user",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("org.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column(
            "role", sa.Text(), nullable=False, server_default=sa.text("'member'")
        ),
        sa.Column("email_verified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("email_verification_token", sa.Text(), nullable=True),
        sa.Column("password_reset_token", sa.Text(), nullable=True),
        sa.Column(
            "password_reset_expires_at", sa.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column("last_login_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "failed_login_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("locked_until", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("role IN ('admin','member')", name="app_user_role_check"),
    )
    op.create_index("app_user_by_org", "app_user", ["org_id"])

    op.create_table(
        "company",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.Text(), nullable=False, unique=True),
        sa.Column("isin", sa.Text(), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "country", sa.String(2), nullable=False, server_default=sa.text("'SE'")
        ),
        sa.Column("market", sa.Text(), nullable=False),
        sa.Column("sector", sa.Text(), nullable=True),
        sa.Column("industry", sa.Text(), nullable=True),
        sa.Column("market_cap_band", sa.Text(), nullable=True),
        sa.Column("yahoo_symbol", sa.Text(), nullable=False),
        sa.Column("mfn_slug", sa.Text(), nullable=True),
        sa.Column("ir_rss_url", sa.Text(), nullable=True),
        sa.Column(
            "active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "market_cap_band IS NULL OR market_cap_band IN ('large','mid','small','micro')",
            name="company_market_cap_band_check",
        ),
    )
    op.execute("CREATE INDEX company_by_market ON company(market) WHERE active = true")

    op.create_table(
        "org_company_access",
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("org.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "company_id",
            sa.BigInteger(),
            sa.ForeignKey("company.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "added_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.execute("ALTER TABLE org_company_access ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE app_user ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY org_company_access_iso ON org_company_access
          USING (org_id = current_setting('app.current_org_id', true)::uuid)
        """
    )
    op.execute(
        """
        CREATE POLICY app_user_iso ON app_user
          USING (org_id = current_setting('app.current_org_id', true)::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS app_user_iso ON app_user")
    op.execute("DROP POLICY IF EXISTS org_company_access_iso ON org_company_access")
    op.execute("ALTER TABLE app_user DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE org_company_access DISABLE ROW LEVEL SECURITY")
    op.drop_table("org_company_access")
    op.execute("DROP INDEX IF EXISTS company_by_market")
    op.drop_table("company")
    op.drop_index("app_user_by_org", table_name="app_user")
    op.drop_table("app_user")
    op.drop_table("org")
