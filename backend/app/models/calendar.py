"""Storage model for scheduled events (catalysts). Insert-only."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, Index, Integer, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    event_type: Mapped[str] = mapped_column(String(48), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    scheduled_on: Mapped[date] = mapped_column(Date, nullable=False)
    scheduled_time: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    url: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    provider_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index(
            "uq_calendar_event_identity",
            "source_id",
            "event_type",
            "scheduled_on",
            "title",
            unique=True,
        ),
        Index("ix_calendar_events_scheduled_on", "scheduled_on"),
    )
