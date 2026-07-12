"""Repositories for permanent research artifacts."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research import WorkspaceSnapshot
from app.schemas.workspace import WorkspaceView


class WorkspaceSnapshotRepository:
    """Reads persisted workspace snapshots without regenerating research."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def latest(self, symbol: str) -> WorkspaceView | None:
        """Return the newest valid snapshot for ``symbol``."""
        snapshot = await self._session.scalar(
            select(WorkspaceSnapshot)
            .where(WorkspaceSnapshot.symbol == symbol.upper())
            .order_by(WorkspaceSnapshot.created_at.desc(), WorkspaceSnapshot.id.desc())
            .limit(1)
        )
        if snapshot is None:
            return None
        return WorkspaceView.model_validate(snapshot.payload)
