"""End-to-end integration tests for the Investment Workspace.

Real stack (API → services → engines → repositories → TimescaleDB) with
Yahoo served by a mock transport. Requires PostgreSQL (see conftest).
"""

from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import func, select

from app.api.deps import (
    get_federal_reserve_connector,
    get_sec_edgar_connector,
    get_yahoo_connector,
    get_yahoo_news_connector,
)
from app.config.settings import Settings
from app.connectors.federal_reserve import FederalReserveConnector
from app.connectors.sec_edgar import SecEdgarConnector
from app.connectors.yahoo import YahooConnector
from app.connectors.yahoo_news import YahooNewsConnector
from app.main import create_app
from app.models.research import WorkspaceSnapshot
from tests.helpers import make_yahoo_chart_json
from tests.test_sec_normalization import make_submissions_json

SYMBOL_CLOSES = [100.0 * (1.002**i) for i in range(320)]
BENCH_CLOSES = [400.0 * (1.001**i) for i in range(320)]

NEWS_RSS = (
    '<?xml version="1.0"?><rss version="2.0"><channel><item>'
    "<title>Semis rally on AI demand</title><link>https://news.test/a</link>"
    "<pubDate>Sat, 11 Jul 2026 19:00:00 +0000</pubDate><guid>news-a</guid>"
    "</item></channel></rss>"
)

TICKER_MAP = '{"0": {"cik_str": 723125, "ticker": "MU", "title": "MICRON TECHNOLOGY INC"}}'


def sec_mock() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("company_tickers.json"):
            return httpx.Response(200, text=TICKER_MAP)
        if "submissions/CIK0000723125" in request.url.path:
            return httpx.Response(
                200, text=make_submissions_json(forms=["8-K", "10-Q"], items=["2.02,9.01", ""])
            )
        return httpx.Response(404, text="{}")

    return httpx.MockTransport(handler)


def news_mock() -> httpx.MockTransport:
    return httpx.MockTransport(lambda request: httpx.Response(200, text=NEWS_RSS))


FED_CALENDAR = (
    '{"events": [{"title": "FOMC Meeting", "type": "FOMC", "month": "2099-07", '
    '"days": "29", "time": "2:00 p.m."}]}'
)


def fed_mock() -> httpx.MockTransport:
    return httpx.MockTransport(lambda request: httpx.Response(200, text=FED_CALENDAR))


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
    app.dependency_overrides[get_sec_edgar_connector] = lambda: SecEdgarConnector(
        client=httpx.AsyncClient(transport=sec_mock()),
        data_base_url="https://sec.test",
        www_base_url="https://sec.test",
    )
    app.dependency_overrides[get_yahoo_news_connector] = lambda: YahooNewsConnector(
        client=httpx.AsyncClient(transport=news_mock()),
        base_url="https://news.test",
    )
    app.dependency_overrides[get_federal_reserve_connector] = lambda: FederalReserveConnector(
        client=httpx.AsyncClient(transport=fed_mock()),
        base_url="https://fed.test",
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
    assert set(sections) == {"technical", "historical", "evidence", "catalysts", "macro"}

    # ADR-010 traceability: every cited evidence id resolves in its section.
    for section in sections.values():
        known = {e["id"] for e in section["evidence"]}
        for statement in section["statements"]:
            assert set(statement["evidence_ids"]) <= known

    # Technical + historical carry real evidence from the mock series.
    assert {"ema50", "ema200", "rsi14"} <= {e["id"] for e in sections["technical"]["evidence"]}
    assert "beta_1y" in {e["id"] for e in sections["historical"]["evidence"]}

    # Company Evidence: filings + coverage with trust levels and links.
    evidence_section = sections["evidence"]
    assert any("SEC filing" in s["text"] for s in evidence_section["statements"])
    assert any("aggregated commentary" in s["text"] for s in evidence_section["statements"])
    assert all(e["trust_level"] is not None and e["url"] for e in evidence_section["evidence"])

    # Catalysts: next FOMC decision from the (mock) Fed calendar; honest gaps.
    catalyst_texts = " ".join(s["text"] for s in sections["catalysts"]["statements"])
    assert "Next FOMC rate decision: 2099-07-29" in catalyst_texts
    assert "Earnings date: not shown" in catalyst_texts

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
