"""End-to-end integration tests for the Investment Workspace.

Real stack (API → services → engines → repositories → TimescaleDB) with
Yahoo served by a mock transport. Requires PostgreSQL (see conftest).
"""

from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import func, select

from app.api.deps import get_yahoo_connector
from app.config.settings import Settings
from app.connectors.yahoo import YahooConnector
from app.main import create_app
from app.models.research import WorkspaceSnapshot
from tests.helpers import make_yahoo_chart_json

SYMBOL_CLOSES = [100.0 * (1.002**i) for i in range(320)]
BENCH_CLOSES = [400.0 * (1.001**i) for i in range(320)]


def yahoo_mock() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "/finance/chart/MU" in path:
            return httpx.Response(
                200, text=make_yahoo_chart_json("MU", SYMBOL_CLOSES, "Micron Technology, Inc.")
            )
        if "/finance/chart/SPY" in path:
            return httpx.Response(
                200, text=make_yahoo_chart_json("SPY", BENCH_CLOSES, "SPDR S&P 500")
            )
        return httpx.Response(404, json={"chart": {"result": None, "error": {"code": "Not Found"}}})

    return httpx.MockTransport(handler)


@pytest.fixture
async def workspace_client(
    integration_db: Settings,
    integration_session: object,  # tables exist + truncated
) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(integration_db)
    app.dependency_overrides[get_yahoo_connector] = lambda: YahooConnector(
        client=httpx.AsyncClient(transport=yahoo_mock()),
        base_url="https://yahoo.test",
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        client.app = app  # type: ignore[attr-defined]
        yield client
    await app.state.http_client.aclose()
    await app.state.engine.dispose()


async def test_workspace_end_to_end(workspace_client: httpx.AsyncClient) -> None:
    response = await workspace_client.get("/api/v1/workspace/mu")  # lowercase on purpose

    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "MU"
    assert body["name"] == "Micron Technology, Inc."
    assert body["quote"]["price"] > 0
    assert len(body["price_history"]) > 200

    sections = {s["id"]: s for s in body["sections"]}
    assert set(sections) == {"technical", "historical", "macro"}

    # ADR-010 traceability: every cited evidence id resolves in its section.
    for section in sections.values():
        known = {e["id"] for e in section["evidence"]}
        for statement in section["statements"]:
            assert set(statement["evidence_ids"]) <= known

    # Technical + historical carry real evidence from the mock series.
    assert {"ema50", "ema200", "rsi14"} <= {e["id"] for e in sections["technical"]["evidence"]}
    assert "beta_1y" in {e["id"] for e in sections["historical"]["evidence"]}

    # Macro section degrades gracefully with no inflation data ingested.
    macro_texts = " ".join(s["text"] for s in sections["macro"]["statements"]).lower()
    assert "no inflation data" in macro_texts


async def test_workspace_snapshot_persisted(workspace_client: httpx.AsyncClient) -> None:
    app: FastAPI = workspace_client.app  # type: ignore[attr-defined]

    first = await workspace_client.get("/api/v1/workspace/MU")
    second = await workspace_client.get("/api/v1/workspace/MU")
    assert first.status_code == second.status_code == 200

    session_factory = app.state.session_factory
    async with session_factory() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(WorkspaceSnapshot)
            .where(WorkspaceSnapshot.symbol == "MU")
        )
    assert count == 2  # research is permanent: every view is kept


async def test_unknown_symbol_is_404(workspace_client: httpx.AsyncClient) -> None:
    response = await workspace_client.get("/api/v1/workspace/NOPE")
    assert response.status_code == 404


async def test_invalid_symbol_is_422(workspace_client: httpx.AsyncClient) -> None:
    response = await workspace_client.get("/api/v1/workspace/BAD!SYM")
    assert response.status_code == 422
