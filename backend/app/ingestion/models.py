from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    Date,
    ForeignKey,
    Numeric,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class PriceBar(Base):
    __tablename__ = "price_bar"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("company.id", ondelete="CASCADE"), nullable=False
    )
    trading_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    high: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    low: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    close: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    adj_close: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    source_row_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        UniqueConstraint("company_id", "trading_date", name="price_bar_unique"),
    )


class NewsItem(Base):
    __tablename__ = "news_item"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("company.id", ondelete="SET NULL"), nullable=True
    )
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    source_row_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    mar_flagged: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    language: Mapped[str | None] = mapped_column(Text, nullable=True)
    also_seen_in: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'::text[]")
    )
    ingested_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        UniqueConstraint("source", "source_row_id", name="news_item_unique"),
    )


class MacroObservation(Base):
    __tablename__ = "macro_observation"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    series_code: Mapped[str] = mapped_column(Text, nullable=False)
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    unit: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    source_row_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        UniqueConstraint(
            "series_code", "observation_date", name="macro_observation_unique"
        ),
    )


__all__ = ["PriceBar", "NewsItem", "MacroObservation"]


_ = Any  # placeholder to keep type imports symmetric across modules
