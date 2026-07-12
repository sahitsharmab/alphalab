"""Persisted user risk plans and their deterministic assessment payloads."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class RiskPlan(Base):
    __tablename__ = "risk_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    account_size: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    entry: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    invalidation: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    target: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    max_dollar_risk: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    assessment: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
