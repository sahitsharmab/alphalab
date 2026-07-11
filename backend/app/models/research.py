"""Research artifacts. Research is permanent — rows are only inserted.

``WorkspaceSnapshot`` stores every generated Investment Workspace view
(ADR-009/010): the seed of the future thesis journal. No user column yet
(single-user, ADR-007); adding one later is a migration, not a rewrite.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class WorkspaceSnapshot(Base):
    __tablename__ = "workspace_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
