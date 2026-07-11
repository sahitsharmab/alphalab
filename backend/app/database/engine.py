"""Async engine and session factory construction.

No engine or session is created at import time — the application factory
owns the engine's lifecycle (no global mutable state).
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_engine(database_url: str) -> AsyncEngine:
    """Create the application's async database engine.

    ``pool_pre_ping`` transparently recovers from dropped connections,
    which matters for a long-lived research platform process.
    """
    return create_async_engine(database_url, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create a session factory bound to the given engine."""
    return async_sessionmaker(engine, expire_on_commit=False)
