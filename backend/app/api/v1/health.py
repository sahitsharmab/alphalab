"""Health endpoint: process liveness plus database readiness."""

import time
from typing import Literal

import structlog
from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = structlog.get_logger(__name__)

router = APIRouter()


class DatabaseHealth(BaseModel):
    """Connectivity status of the primary database."""

    status: Literal["ok", "unavailable"]
    latency_ms: float | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    """Overall platform health."""

    status: Literal["ok", "degraded"]
    environment: str
    version: str
    database: DatabaseHealth


async def check_database(engine: AsyncEngine) -> DatabaseHealth:
    """Execute a trivial query to verify database connectivity."""
    start = time.perf_counter()
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning("database_health_check_failed", error=str(exc))
        return DatabaseHealth(status="unavailable", error=str(exc))
    latency_ms = round((time.perf_counter() - start) * 1000, 2)
    return DatabaseHealth(status="ok", latency_ms=latency_ms)


@router.get("/health")
async def health(request: Request) -> HealthResponse:
    """Report process liveness and database readiness."""
    database = await check_database(request.app.state.engine)
    return HealthResponse(
        status="ok" if database.status == "ok" else "degraded",
        environment=str(request.app.state.settings.env),
        version=request.app.version,
        database=database,
    )
