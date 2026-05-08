"""phase-2 chat orchestrator: chat_thread + chat_turn + chat_engine_call (with RLS)

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_thread",
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
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("app_user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "company_id",
            sa.BigInteger(),
            sa.ForeignKey("company.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column(
            "is_archived",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
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
    )
    op.create_index(
        "chat_thread_recent",
        "chat_thread",
        ["org_id", "user_id", sa.text("updated_at DESC")],
    )

    op.create_table(
        "chat_turn",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "thread_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_thread.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("idx", sa.Integer(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_calls", postgresql.JSONB(), nullable=True),
        sa.Column("tool_call_id", sa.Text(), nullable=True),
        sa.Column("tool_name", sa.Text(), nullable=True),
        sa.Column("citation_spans", postgresql.JSONB(), nullable=True),
        sa.Column("llm_provider", sa.Text(), nullable=True),
        sa.Column("llm_model", sa.Text(), nullable=True),
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
            sa.Numeric(10, 4),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("finish_reason", sa.Text(), nullable=True),
        sa.Column("warning", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "role IN ('user','assistant','tool','system')",
            name="chat_turn_role_check",
        ),
        sa.UniqueConstraint("thread_id", "idx", name="chat_turn_idx_unique"),
    )
    op.create_index("chat_turn_lookup", "chat_turn", ["thread_id", "created_at"])

    op.create_table(
        "chat_engine_call",
        sa.Column(
            "turn_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_turn.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "engine_call_id",
            sa.Text(),
            sa.ForeignKey("engine_call.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.execute("ALTER TABLE chat_thread ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE chat_turn ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE chat_engine_call ENABLE ROW LEVEL SECURITY")

    op.execute(
        """
        CREATE POLICY chat_thread_iso ON chat_thread
          USING (org_id = current_setting('app.current_org_id', true)::uuid)
          WITH CHECK (org_id = current_setting('app.current_org_id', true)::uuid)
        """
    )
    op.execute(
        """
        CREATE POLICY chat_turn_iso ON chat_turn
          USING (
            thread_id IN (
              SELECT id FROM chat_thread
              WHERE org_id = current_setting('app.current_org_id', true)::uuid
            )
          )
          WITH CHECK (
            thread_id IN (
              SELECT id FROM chat_thread
              WHERE org_id = current_setting('app.current_org_id', true)::uuid
            )
          )
        """
    )
    op.execute(
        """
        CREATE POLICY chat_engine_call_iso ON chat_engine_call
          USING (
            turn_id IN (
              SELECT t.id FROM chat_turn t
              JOIN chat_thread th ON th.id = t.thread_id
              WHERE th.org_id = current_setting('app.current_org_id', true)::uuid
            )
          )
          WITH CHECK (
            turn_id IN (
              SELECT t.id FROM chat_turn t
              JOIN chat_thread th ON th.id = t.thread_id
              WHERE th.org_id = current_setting('app.current_org_id', true)::uuid
            )
          )
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS chat_engine_call_iso ON chat_engine_call")
    op.execute("DROP POLICY IF EXISTS chat_turn_iso ON chat_turn")
    op.execute("DROP POLICY IF EXISTS chat_thread_iso ON chat_thread")
    op.drop_table("chat_engine_call")
    op.execute("DROP INDEX IF EXISTS chat_turn_lookup")
    op.drop_table("chat_turn")
    op.execute("DROP INDEX IF EXISTS chat_thread_recent")
    op.drop_table("chat_thread")
