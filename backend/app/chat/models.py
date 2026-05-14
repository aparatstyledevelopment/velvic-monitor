from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ChatThread(Base):
    __tablename__ = "chat_thread"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    org_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("org.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="CASCADE"),
        nullable=False,
    )
    company_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("company.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    is_archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class ChatTurn(Base):
    __tablename__ = "chat_turn"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    thread_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("chat_thread.id", ondelete="CASCADE"),
        nullable=False,
    )
    idx: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_calls: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True
    )
    tool_call_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    citation_spans: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True
    )
    llm_provider: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    cost_cents: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, server_default=text("0")
    )
    finish_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    warning: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_followups: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('user','assistant','tool','system')",
            name="chat_turn_role_check",
        ),
        UniqueConstraint("thread_id", "idx", name="chat_turn_idx_unique"),
    )


class ChatEngineCall(Base):
    __tablename__ = "chat_engine_call"

    turn_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("chat_turn.id", ondelete="CASCADE"),
        primary_key=True,
    )
    engine_call_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("engine_call.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class LLMCallLog(Base):
    """One row per LLM call (SDK turn or single-shot Messages call).

    Overview only — no prompts, no responses, no tool inputs. Surfaces the
    Settings page totals and gives finops a cost trail without retaining
    sensitive payloads.

    `org_id` is nullable so system-level pipeline calls (the daily briefing
    composer, news summaries run from Celery) still get recorded; they
    aggregate as "system" in the summary endpoint.
    """

    __tablename__ = "llm_call_log"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    org_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("org.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="SET NULL"),
        nullable=True,
    )
    thread_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("chat_thread.id", ondelete="SET NULL"),
        nullable=True,
    )
    company_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("company.id", ondelete="SET NULL"),
        nullable=True,
    )
    surface: Mapped[str] = mapped_column(Text, nullable=False)
    transport: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    cost_cents: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, server_default=text("0")
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        CheckConstraint(
            "surface IN ('chat_orchestrator','chat_orchestrator_retry',"
            "'topic_gate','thread_title','briefing_narrative',"
            "'briefing_narrative_retry','news_summary')",
            name="llm_call_log_surface_check",
        ),
        CheckConstraint(
            "transport IN ('sdk','messages_api')",
            name="llm_call_log_transport_check",
        ),
    )


__all__ = ["ChatThread", "ChatTurn", "ChatEngineCall", "LLMCallLog"]
