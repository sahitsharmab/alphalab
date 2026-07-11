"""Shared test fixtures.

Unit tests never touch a real database or network: the ``settings``
fixture points at a closed port and behavior is exercised with fakes.

Integration tests (fixtures prefixed ``integration_``) require a running
PostgreSQL/TimescaleDB server. Locally they skip when no server is
reachable; in CI set ``ALPHALAB_REQUIRE_DB=1`` so a misconfigured service
fails loudly instead of silently skipping.
"""

import asyncio
import os
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import asyncpg
import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Environment, Settings
from app.database.engine import create_engine, create_session_factory
from app.main import create_app

BACKEND_DIR = Path(__file__).resolve().parent.parent


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


# --- Integration fixtures (real PostgreSQL/TimescaleDB) -------------------


@pytest.fixture(scope="session")
def integration_settings() -> Settings:
    """Settings for a dedicated ``*_test`` database on the configured server."""
    base = Settings(_env_file=None)  # type: ignore[call-arg]
    return base.model_copy(update={"env": Environment.TEST, "db_name": f"{base.db_name}_test"})


@pytest.fixture(scope="session")
def integration_db(integration_settings: Settings) -> Settings:
    """Create a fresh, fully migrated test database; skip if no server."""

    async def recreate_database() -> bool:
        try:
            connection = await asyncpg.connect(
                host=integration_settings.db_host,
                port=integration_settings.db_port,
                user=integration_settings.db_user,
                password=integration_settings.db_password,
                database="postgres",
                timeout=5,
            )
        except OSError:
            return False
        try:
            await connection.execute(
                f'DROP DATABASE IF EXISTS "{integration_settings.db_name}" WITH (FORCE)'
            )
            await connection.execute(f'CREATE DATABASE "{integration_settings.db_name}"')
        finally:
            await connection.close()
        return True

    if not asyncio.run(recreate_database()):
        if os.environ.get("ALPHALAB_REQUIRE_DB") == "1":
            pytest.fail("ALPHALAB_REQUIRE_DB=1 but no PostgreSQL server is reachable")
        pytest.skip("PostgreSQL not reachable; skipping integration tests")

    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env={
            **os.environ,
            "ALPHALAB_DB_HOST": integration_settings.db_host,
            "ALPHALAB_DB_PORT": str(integration_settings.db_port),
            "ALPHALAB_DB_USER": integration_settings.db_user,
            "ALPHALAB_DB_PASSWORD": integration_settings.db_password,
            "ALPHALAB_DB_NAME": integration_settings.db_name,
        },
        check=True,
    )
    return integration_settings


@pytest.fixture
async def integration_session(integration_db: Settings) -> AsyncIterator[AsyncSession]:
    """A session against a clean (truncated) test database."""
    engine = create_engine(integration_db.database_url)
    async with engine.connect() as connection:
        await connection.execute(
            text("TRUNCATE macro_observations, raw_payloads, macro_series CASCADE")
        )
        await connection.commit()
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        yield session
    await engine.dispose()
