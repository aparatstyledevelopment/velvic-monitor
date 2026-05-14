"""phase-3 expansion: chat_turn.suggested_followups (text[])

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-09

Stores the assistant's 3 contextual follow-up question suggestions, used
by the frontend to render interactive chips after the turn settles.
Suggestions are prose questions, not facts: they don't carry numbers
and don't need engine_call_ids. Nullable for backwards compatibility
with turns persisted before this migration.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "chat_turn",
        sa.Column(
            "suggested_followups",
            postgresql.ARRAY(sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("chat_turn", "suggested_followups")
