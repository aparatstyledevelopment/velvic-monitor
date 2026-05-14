"""llm call logging table

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-14

One row per LLM call (SDK turn or single-shot Messages call). Stores
overview only — no prompts, no responses. Surfaces the Settings page
totals and gives finops a cost trail without retaining sensitive
payloads.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_call_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("org.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("app_user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "thread_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_thread.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "company_id",
            sa.BigInteger(),
            sa.ForeignKey("company.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("surface", sa.Text(), nullable=False),
        sa.Column("transport", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column(
            "prompt_tokens",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "completion_tokens",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "cost_cents",
            sa.Numeric(12, 4),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "surface IN ('chat_orchestrator','chat_orchestrator_retry',"
            "'topic_gate','thread_title','briefing_narrative',"
            "'briefing_narrative_retry','news_summary')",
            name="llm_call_log_surface_check",
        ),
        sa.CheckConstraint(
            "transport IN ('sdk','messages_api')",
            name="llm_call_log_transport_check",
        ),
    )
    op.create_index(
        "llm_call_log_org_created_idx",
        "llm_call_log",
        ["org_id", "created_at"],
    )
    op.create_index(
        "llm_call_log_surface_idx",
        "llm_call_log",
        ["surface"],
    )


def downgrade() -> None:
    op.drop_index("llm_call_log_surface_idx", table_name="llm_call_log")
    op.drop_index("llm_call_log_org_created_idx", table_name="llm_call_log")
    op.drop_table("llm_call_log")
