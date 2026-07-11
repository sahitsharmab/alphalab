"""End-to-end integration tests for the macro vertical slice.

Exercises the real stack — API → service → connector (mock transport) →
normalization → repositories → PostgreSQL/TimescaleDB — including the
bitemporal as-of semantics of ADR-004.

Requires a reachable PostgreSQL server (see conftest); skips otherwise.
"""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from app.api.deps import get_nowflation_connector
from app.config.settings import Settings
from app.connectors.nowflation import NowflationConnector
from app.main import create_app

FIXTURE = Path(__file__).parent / "fixtures" / "nowflation_headline_sample.csv"

CSV_V1 = FIXTURE.read_text()
# One revised value: 2019-01-03 index 101.7 -> 101.75 (a provider revision).
CSV_V2 = CSV_V1.replace("2019-01-03,101.7,", "2019-01-03,101.75,")


@pytest.fixture
async def integration_client(
    integration_db: Settings,
    integration_session: object,  # ensures tables exist and are truncated
) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(integration_db)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        client.app = app  # type: ignore[attr-defined]
        yield client
    await app.state.http_client.aclose()
    await app.state.engine.dispose()


def use_csv(app: FastAPI, csv_text: str) -> None:
    """Point the Nowflation connector at an in-memory CSV."""

    def override() -> NowflationConnector:
        transport = httpx.MockTransport(lambda request: httpx.Response(200, text=csv_text))
        return NowflationConnector(
            client=httpx.AsyncClient(transport=transport),
            base_url="https://nowflation.test",
        )

    app.dependency_overrides[get_nowflation_connector] = override


async def test_ingest_then_query_full_slice(integration_client: httpx.AsyncClient) -> None:
    app: FastAPI = integration_client.app  # type: ignore[attr-defined]
    use_csv(app, CSV_V1)

    ingest = await integration_client.post("/api/v1/macro/ingest/nowflation")
    assert ingest.status_code == 200
    report = ingest.json()
    assert report["provider"] == "nowflation"
    assert report["raw_payload_reused"] is False
    assert report["observations_parsed"] == 15
    assert report["observations_inserted"] == 15

    series = await integration_client.get("/api/v1/macro/series")
    assert series.status_code == 200
    assert {item["series_id"] for item in series.json()} == {
        "nowflation.headline.index",
        "nowflation.headline.yoy",
        "nowflation.headline.coverage",
    }

    observations = await integration_client.get(
        "/api/v1/macro/series/nowflation.headline.index/observations"
    )
    assert observations.status_code == 200
    body = observations.json()
    assert len(body) == 6
    assert body[0]["observation_date"] == "2018-01-01"
    assert body[-1]["observation_date"] == "2019-01-03"
    assert body[-1]["value"] == "101.7"

    missing = await integration_client.get("/api/v1/macro/series/nope/observations")
    assert missing.status_code == 404


async def test_reingesting_identical_data_is_idempotent(
    integration_client: httpx.AsyncClient,
) -> None:
    app: FastAPI = integration_client.app  # type: ignore[attr-defined]
    use_csv(app, CSV_V1)

    first = (await integration_client.post("/api/v1/macro/ingest/nowflation")).json()
    second = (await integration_client.post("/api/v1/macro/ingest/nowflation")).json()

    assert first["observations_inserted"] == 15
    assert second["observations_inserted"] == 0
    assert second["raw_payload_reused"] is True
    assert second["raw_payload_id"] == first["raw_payload_id"]


async def test_revisions_are_bitemporal_and_as_of_queryable(
    integration_client: httpx.AsyncClient,
) -> None:
    app: FastAPI = integration_client.app  # type: ignore[attr-defined]

    use_csv(app, CSV_V1)
    first = (await integration_client.post("/api/v1/macro/ingest/nowflation")).json()
    first_as_of = first["retrieved_at"]

    await asyncio.sleep(0.02)  # guarantee a strictly later as_of
    use_csv(app, CSV_V2)
    second = (await integration_client.post("/api/v1/macro/ingest/nowflation")).json()
    assert second["observations_inserted"] == 1  # only the revised value

    # Latest knowledge: the revision wins.
    latest = (
        await integration_client.get("/api/v1/macro/series/nowflation.headline.index/observations")
    ).json()
    assert latest[-1]["value"] == "101.75"

    # Knowledge as of the first ingestion: the original value, no look-ahead.
    historical = (
        await integration_client.get(
            "/api/v1/macro/series/nowflation.headline.index/observations",
            params={"as_of": first_as_of},
        )
    ).json()
    assert historical[-1]["value"] == "101.7"
    assert len(historical) == 6
