"""Normalizes Nowflation CSV exports into ``MacroObservationIn`` values.

Headline CSV columns (verified 2026-07-11):

    date,index_value,yoy,coverage_pct

* ``index_value`` — daily gauge, base January 2018 = 100
* ``yoy`` — year-over-year change as a fraction (0.0178 = 1.78%); empty
  for the first year of the series
* ``coverage_pct`` — fraction of the CPI basket covered by live sources
"""

import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation

from app.normalization import NormalizationError
from app.schemas.macro import MacroObservationIn, SeriesDefinition

SERIES_HEADLINE_INDEX = "nowflation.headline.index"
SERIES_HEADLINE_YOY = "nowflation.headline.yoy"
SERIES_HEADLINE_COVERAGE = "nowflation.headline.coverage"

NOWFLATION_SERIES: tuple[SeriesDefinition, ...] = (
    SeriesDefinition(
        series_id=SERIES_HEADLINE_INDEX,
        provider="nowflation",
        name="Nowflation Headline Gauge",
        unit="index (Jan 2018 = 100)",
        description="Daily market-price inflation index built from ~1,079 public series.",
    ),
    SeriesDefinition(
        series_id=SERIES_HEADLINE_YOY,
        provider="nowflation",
        name="Nowflation Headline YoY",
        unit="fraction (YoY)",
        description="Year-over-year change of the headline gauge; 0.0178 = 1.78%.",
    ),
    SeriesDefinition(
        series_id=SERIES_HEADLINE_COVERAGE,
        provider="nowflation",
        name="Nowflation Basket Coverage",
        unit="fraction",
        description="Share of the CPI basket covered by live data sources.",
    ),
)

_COLUMN_TO_SERIES = {
    "index_value": SERIES_HEADLINE_INDEX,
    "yoy": SERIES_HEADLINE_YOY,
    "coverage_pct": SERIES_HEADLINE_COVERAGE,
}

_EXPECTED_COLUMNS = frozenset({"date", *_COLUMN_TO_SERIES})


def normalize_headline_csv(csv_text: str) -> list[MacroObservationIn]:
    """Parse the headline CSV into normalized observations.

    Empty cells (e.g. ``yoy`` during the first year) are skipped, not
    treated as zero. Malformed rows fail loudly: silent data corruption is
    worse than a failed ingestion run.
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames is None or not _EXPECTED_COLUMNS.issubset(reader.fieldnames):
        raise NormalizationError(
            f"unexpected headline CSV columns: {reader.fieldnames!r}; "
            f"expected at least {sorted(_EXPECTED_COLUMNS)}"
        )

    observations: list[MacroObservationIn] = []
    for line_number, row in enumerate(reader, start=2):
        raw_date = (row.get("date") or "").strip()
        if not raw_date:
            continue  # tolerate trailing blank lines
        try:
            observation_date = date.fromisoformat(raw_date)
        except ValueError as exc:
            raise NormalizationError(f"line {line_number}: invalid date {raw_date!r}") from exc

        for column, series_id in _COLUMN_TO_SERIES.items():
            cell = (row.get(column) or "").strip()
            if not cell:
                continue
            try:
                value = Decimal(cell)
            except InvalidOperation as exc:
                raise NormalizationError(
                    f"line {line_number}: invalid {column} value {cell!r}"
                ) from exc
            observations.append(
                MacroObservationIn(
                    series_id=series_id,
                    observation_date=observation_date,
                    value=value,
                )
            )
    return observations
