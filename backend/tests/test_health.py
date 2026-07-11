"""Tests for the /api/v1/health endpoint."""

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.v1 import health as health_module


async def test_health_reports_ok_when_database_reachable(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_check(engine: AsyncEngine) -> health_module.DatabaseHealth:
        return health_module.DatabaseHealth(status="ok", latency_ms=0.42)

    monkeypatch.setattr(health_module, "check_database", fake_check)

    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["environment"] == "test"
    assert body["database"] == {"status": "ok", "latency_ms": 0.42, "error": None}


async def test_health_reports_degraded_when_database_unreachable(
    client: httpx.AsyncClient,
) -> None:
    # conftest points the engine at an unreachable port — no mocking needed.
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database"]["status"] == "unavailable"
    assert body["database"]["error"]


async def test_openapi_docs_are_exposed(client: httpx.AsyncClient) -> None:
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "AlphaLab"
