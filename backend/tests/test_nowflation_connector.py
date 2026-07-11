"""Unit tests for the Nowflation connector (no real network: MockTransport)."""

import hashlib
from pathlib import Path

import httpx
import pytest

from app.connectors.base import ConnectorError
from app.connectors.nowflation import DATASET_HEADLINE, NowflationConnector

FIXTURE = Path(__file__).parent / "fixtures" / "nowflation_headline_sample.csv"
BASE_URL = "https://nowflation.test"


def make_connector(handler: httpx.MockTransport) -> NowflationConnector:
    client = httpx.AsyncClient(transport=handler)
    return NowflationConnector(client=client, base_url=BASE_URL, backoff_base_seconds=0.01)


async def test_fetch_headline_returns_raw_csv_with_metadata() -> None:
    csv_text = FIXTURE.read_text()
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=csv_text))

    result = await make_connector(transport).fetch_headline()

    assert result.provider == "nowflation"
    assert result.dataset == DATASET_HEADLINE
    assert result.url == f"{BASE_URL}/api/inflation/export/headline.csv"
    assert result.content == csv_text
    assert result.content_hash == hashlib.sha256(csv_text.encode()).hexdigest()
    assert result.retrieved_at.tzinfo is not None


async def test_fetch_retries_transient_errors_then_succeeds() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503)
        return httpx.Response(200, text="date,index_value,yoy,coverage_pct\n")

    result = await make_connector(httpx.MockTransport(handler)).fetch_headline()

    assert attempts == 2
    assert result.content.startswith("date,")


async def test_fetch_fails_after_exhausting_retries() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(500))

    with pytest.raises(ConnectorError, match="failed after 3 attempts"):
        await make_connector(transport).fetch_headline()


async def test_fetch_does_not_retry_fatal_status() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(404)

    with pytest.raises(ConnectorError, match="HTTP 404"):
        await make_connector(httpx.MockTransport(handler)).fetch_headline()
    assert attempts == 1


async def test_health_reports_unavailable_on_failure() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(500))

    health = await make_connector(transport).health()

    assert health.status == "unavailable"
    assert health.error is not None
