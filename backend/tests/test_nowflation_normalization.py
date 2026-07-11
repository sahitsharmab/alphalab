"""Unit tests for Nowflation CSV normalization."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.normalization.nowflation import (
    SERIES_HEADLINE_COVERAGE,
    SERIES_HEADLINE_INDEX,
    SERIES_HEADLINE_YOY,
    NormalizationError,
    normalize_headline_csv,
)

FIXTURE = Path(__file__).parent / "fixtures" / "nowflation_headline_sample.csv"


def test_normalizes_all_populated_cells() -> None:
    observations = normalize_headline_csv(FIXTURE.read_text())

    by_series = dict.fromkeys(
        (SERIES_HEADLINE_INDEX, SERIES_HEADLINE_YOY, SERIES_HEADLINE_COVERAGE), 0
    )
    for observation in observations:
        by_series[observation.series_id] += 1

    # 6 rows: index + coverage always populated, yoy only for the 2019 rows.
    assert by_series[SERIES_HEADLINE_INDEX] == 6
    assert by_series[SERIES_HEADLINE_COVERAGE] == 6
    assert by_series[SERIES_HEADLINE_YOY] == 3
    assert len(observations) == 15


def test_values_are_exact_decimals() -> None:
    observations = normalize_headline_csv(FIXTURE.read_text())

    index_2019_01_02 = next(
        item
        for item in observations
        if item.series_id == SERIES_HEADLINE_INDEX and item.observation_date == date(2019, 1, 2)
    )
    assert index_2019_01_02.value == Decimal("101.6")


def test_empty_yoy_cells_are_skipped_not_zero() -> None:
    observations = normalize_headline_csv(FIXTURE.read_text())

    yoy_dates = {
        item.observation_date for item in observations if item.series_id == SERIES_HEADLINE_YOY
    }
    assert date(2018, 1, 1) not in yoy_dates
    assert date(2019, 1, 1) in yoy_dates


def test_unexpected_columns_raise() -> None:
    with pytest.raises(NormalizationError, match="unexpected headline CSV columns"):
        normalize_headline_csv("foo,bar\n1,2\n")


def test_invalid_number_raises_with_line_context() -> None:
    bad = "date,index_value,yoy,coverage_pct\n2020-01-01,not-a-number,,0.3\n"
    with pytest.raises(NormalizationError, match="line 2"):
        normalize_headline_csv(bad)


def test_invalid_date_raises_with_line_context() -> None:
    bad = "date,index_value,yoy,coverage_pct\nJanuary,100,,0.3\n"
    with pytest.raises(NormalizationError, match="line 2"):
        normalize_headline_csv(bad)
