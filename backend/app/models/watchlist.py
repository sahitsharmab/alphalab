"""Single-user watchlist persistence (ADR-007)."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    symbol: Mapped[str] = mapped_column(
        String(16), ForeignKey("instruments.symbol"), primary_key=True
    )
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
