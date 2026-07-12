"""FastAPI dependency providers.

All shared resources (engine, session factory, HTTP client) live on
``app.state``, created by the application factory — no module-level
singletons.
"""

from collections.abc import AsyncIterator

import httpx
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.nowflation import NowflationConnector
from app.connectors.sec_edgar import SecEdgarConnector
from app.connectors.yahoo import YahooConnector


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield a database session scoped to the request."""
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session


def get_http_client(request: Request) -> httpx.AsyncClient:
    """Shared outbound HTTP client (connection pooling, timeouts)."""
    client: httpx.AsyncClient = request.app.state.http_client
    return client


def get_nowflation_connector(request: Request) -> NowflationConnector:
    settings = request.app.state.settings
    return NowflationConnector(
        client=get_http_client(request),
        base_url=settings.nowflation_base_url,
    )


def get_yahoo_connector(request: Request) -> YahooConnector:
    settings = request.app.state.settings
    return YahooConnector(
        client=get_http_client(request),
        base_url=settings.yahoo_base_url,
    )


def get_sec_edgar_connector(request: Request) -> SecEdgarConnector:
    settings = request.app.state.settings
    return SecEdgarConnector(
        client=get_http_client(request),
        data_base_url=settings.sec_data_base_url,
        www_base_url=settings.sec_www_base_url,
        user_agent=settings.sec_user_agent,
    )
