"""Integration tests for the evidence slice (API → service → storage).

Real PostgreSQL; SEC EDGAR served by a mock transport.
"""

import json
from collections.abc import AsyncIterator

import httpx
import pytest

from app.api.deps import get_sec_edgar_connector
from app.config.settings import Settings
from app.connectors.sec_edgar import SecEdgarConnector
from app.main import create_app
from tests.test_sec_normalization import make_submissions_json

TICKER_MAP = json.dumps(
    {"0": {"cik_str": 723125, "ticker": "MU", "title": "MICRON TECHNOLOGY INC"}}
)
SUBMISSIONS = make_submissions_json(
    forms=["8-K", "10-Q", "4", "10-K"],
    items=["2.02,9.01", "", "", ""],
)


def sec_mock() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("company_tickers.json"):
            return httpx.Response(200, text=TICKER_MAP)
        if "submissions/CIK0000723125" in path:
            return httpx.Response(200, text=SUBMISSIONS)
        return httpx.Response(404, text="{}")

    return httpx.MockTransport(handler)


@pytest.fixture
async def evidence_client(
    integration_db: Settings,
    integration_session: object,
) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(integration_db)
    app.dependency_overrides[get_sec_edgar_connector] = lambda: SecEdgarConnector(
        client=httpx.AsyncClient(transport=sec_mock()),
        data_base_url="https://sec.test",
        www_base_url="https://sec.test",
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        client.app = app  # type: ignore[attr-defined]
        yield client
    await app.state.http_client.aclose()
    await app.state.engine.dispose()


async def test_evidence_end_to_end(evidence_client: httpx.AsyncClient) -> None:
    response = await evidence_client.get("/api/v1/evidence/mu")

    assert response.status_code == 200
    body = response.json()
    assert body["ingestion"]["records_parsed"] == 3  # Form 4 excluded
    assert body["ingestion"]["records_inserted"] == 3

    records = body["records"]
    assert len(records) == 3
    first = records[0]
    assert first["source_id"] == "sec_edgar"
    assert first["source_name"] == "SEC EDGAR"
    assert first["trust_level"] == 10  # registry-driven (ADR-011)
    assert {r["category"] for r in records} == {"earnings", "sec_filing"}
    assert all(
        {"entity_type": "instrument", "entity_key": "MU", "role": "subject"} in r["entities"]
        for r in records
    )


async def test_evidence_reingest_is_idempotent(evidence_client: httpx.AsyncClient) -> None:
    first = (await evidence_client.get("/api/v1/evidence/MU")).json()
    # Second call within the staleness window: no fetch at all.
    second = (await evidence_client.get("/api/v1/evidence/MU")).json()
    # Forced refresh: fetches again but inserts nothing new.
    third = (await evidence_client.get("/api/v1/evidence/MU?refresh=true")).json()

    assert first["ingestion"]["records_inserted"] == 3
    assert second["ingestion"] is None
    assert third["ingestion"]["records_inserted"] == 0
    assert len(third["records"]) == 3


async def test_evidence_filters(evidence_client: httpx.AsyncClient) -> None:
    await evidence_client.get("/api/v1/evidence/MU")

    earnings_only = (await evidence_client.get("/api/v1/evidence/MU?category=earnings")).json()
    assert {r["category"] for r in earnings_only["records"]} == {"earnings"}

    at_boundary = (await evidence_client.get("/api/v1/evidence/MU?min_trust=10")).json()
    assert len(at_boundary["records"]) == 3  # SEC EDGAR is trust 10

    out_of_range = await evidence_client.get("/api/v1/evidence/MU?min_trust=11")
    assert out_of_range.status_code == 422  # trust scale is 0-10


async def test_unknown_symbol_is_404(evidence_client: httpx.AsyncClient) -> None:
    response = await evidence_client.get("/api/v1/evidence/ZZZZ")
    assert response.status_code == 404
    assert "no SEC CIK" in response.json()["detail"]
