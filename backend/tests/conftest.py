"""Shared test fixtures.

Tests never touch a real database or network: the settings fixture points
at a closed port, and DB-dependent behavior is exercised via monkeypatching.
"""

from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI

from app.config.settings import Environment, Settings
from app.main import create_app


@pytest.fixture
def settings() -> Settings:
    """Deterministic test settings; DB port is intentionally unreachable."""
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        env=Environment.TEST,
        db_host="127.0.0.1",
        db_port=1,
    )


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
