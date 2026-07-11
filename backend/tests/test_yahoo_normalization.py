"""Unit tests for Yahoo chart normalization."""

import json

import pytest

from app.normalization import NormalizationError
from app.normalization.yahoo import parse_chart
from tests.helpers import make_yahoo_chart_json


def test_parses_instrument_and_bars() -> None:
    payload = make_yahoo_chart_json("MU", [100.0, 101.5, 99.75], name="Micron Technology, Inc.")

    instrument, bars = parse_chart(payload)

    assert instrument.symbol == "MU"
    assert instrument.name == "Micron Technology, Inc."
    assert instrument.currency == "USD"
    assert len(bars) == 3
    assert float(bars[-1].close) == 99.75
    assert bars[0].bar_date < bars[-1].bar_date


def test_skips_null_close_rows() -> None:
    payload = json.loads(make_yahoo_chart_json("MU", [100.0, 101.0, 102.0]))
    payload["chart"]["result"][0]["indicators"]["quote"][0]["close"][1] = None
    _, bars = parse_chart(json.dumps(payload))
    assert len(bars) == 2


def test_provider_error_raises() -> None:
    payload = json.dumps(
        {"chart": {"result": None, "error": {"code": "Not Found", "description": "No data"}}}
    )
    with pytest.raises(NormalizationError, match="provider error"):
        parse_chart(payload)


def test_invalid_json_raises() -> None:
    with pytest.raises(NormalizationError, match="invalid JSON"):
        parse_chart("<html>rate limited</html>")


def test_missing_adjclose_falls_back_to_close() -> None:
    payload = json.loads(make_yahoo_chart_json("MU", [100.0, 101.0]))
    del payload["chart"]["result"][0]["indicators"]["adjclose"]
    _, bars = parse_chart(json.dumps(payload))
    assert [float(b.adj_close) for b in bars] == [100.0, 101.0]
