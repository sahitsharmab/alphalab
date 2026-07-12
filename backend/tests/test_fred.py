"""Unit tests: FRED connector (key hygiene), normalization, catalyst playbook."""

import json
from datetime import date

import httpx
import pytest

from app.config.catalyst_playbook import PLAYBOOK, PLAYBOOK_VERSION, get_assessment
from app.connectors.base import ConnectorError
from app.connectors.fred import FredConnector
from app.normalization import NormalizationError
from app.normalization.fred import TRACKED_RELEASES, parse_release_dates
from app.schemas.calendar import CalendarEventType

API_KEY = "0123456789abcdef0123456789abcdef"
CPI = next(r for r in TRACKED_RELEASES if r.kind == "CPI")


def make_connector(transport: httpx.MockTransport) -> FredConnector:
    client = httpx.AsyncClient(transport=transport)
    return FredConnector(
        client=client, api_key=API_KEY, base_url="https://fred.test", backoff_base_seconds=0.01
    )


def release_dates_json(release_id: int, dates: list[str]) -> str:
    return json.dumps({"release_dates": [{"release_id": release_id, "date": d} for d in dates]})


# --- Connector: the API key must never leak into recorded URLs or errors ---


async def test_fetch_sends_key_but_never_records_it() -> None:
    seen_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        return httpx.Response(200, text=release_dates_json(10, ["2026-07-14"]))

    result = await make_connector(httpx.MockTransport(handler)).fetch_release_dates(
        10, date(2026, 7, 12)
    )

    assert f"api_key={API_KEY}" in seen_urls[0]  # sent to the provider
    assert API_KEY not in result.url  # never stored/logged
    assert "release_id=10" in result.url  # non-secret provenance retained
    assert "realtime_start=2026-07-12" in result.url


async def test_fetch_error_message_does_not_contain_key() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(403, text="denied"))

    with pytest.raises(ConnectorError) as excinfo:
        await make_connector(transport).fetch_release_dates(10, date(2026, 7, 12))
    assert API_KEY not in str(excinfo.value)


def test_connector_requires_a_key() -> None:
    with pytest.raises(ValueError, match="API key"):
        FredConnector(client=httpx.AsyncClient(), api_key="")


# --- Normalization ---


def test_parse_release_dates_happy_path() -> None:
    events = parse_release_dates(release_dates_json(10, ["2026-07-14", "2026-08-12"]), CPI)

    assert [e.scheduled_on for e in events] == [date(2026, 7, 14), date(2026, 8, 12)]
    for event in events:
        assert event.source_id == "fred"
        assert event.event_type is CalendarEventType.ECONOMIC_RELEASE
        assert event.title == "Consumer Price Index (CPI)"
        assert event.provider_metadata == {"release_id": 10, "kind": "CPI"}
        assert event.url == "https://fred.stlouisfed.org/release?rid=10"
        assert event.scheduled_time == ""  # FRED publishes dates only


def test_parse_release_dates_rejects_garbage() -> None:
    with pytest.raises(NormalizationError, match="invalid JSON"):
        parse_release_dates("<html>blocked</html>", CPI)
    with pytest.raises(NormalizationError, match="no release_dates"):
        parse_release_dates('{"releases": []}', CPI)
    with pytest.raises(NormalizationError, match="invalid date"):
        parse_release_dates(release_dates_json(10, ["not-a-date"]), CPI)


def test_parse_release_dates_rejects_wrong_release() -> None:
    with pytest.raises(NormalizationError, match="expected release_id 10"):
        parse_release_dates(release_dates_json(46, ["2026-07-15"]), CPI)


# --- Catalyst playbook: complete, versioned, honest ---


def test_every_tracked_release_has_a_playbook_entry() -> None:
    for release in TRACKED_RELEASES:
        assert release.kind in PLAYBOOK, f"no playbook entry for {release.kind}"


def test_fed_event_kinds_have_playbook_entries() -> None:
    for kind in ("FOMC_MEETING", "FOMC_MINUTES", "BEIGE_BOOK"):
        assert kind in PLAYBOOK


def test_playbook_entries_are_complete_and_versioned() -> None:
    for kind, entry in PLAYBOOK.items():
        assert entry.kind == kind
        assert entry.playbook_version == PLAYBOOK_VERSION
        assert entry.importance in {"very high", "high", "medium"}
        assert entry.why_it_matters and entry.horizon
        assert entry.transmission and entry.watch
        assert entry.supportive_scenario and entry.adverse_scenario


def test_playbook_never_calls_qqq_the_nasdaq() -> None:
    """Proxies must be labeled as proxies (ADR-016 guardrail)."""
    for entry in PLAYBOOK.values():
        for item in entry.watch:
            if "QQQ" in item:
                assert "prox" in item.lower()  # "proxy" or "proxies"


def test_unknown_kind_has_no_assessment() -> None:
    assert get_assessment("NOT_A_KIND") is None
