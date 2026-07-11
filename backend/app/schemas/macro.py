"""Domain schemas for macroeconomic data.

``MacroObservationIn`` is the normalized unit every macro connector's data
is reduced to (ADR-002 / normalization layer). Observations are bitemporal
(ADR-004): the ``as_of`` dimension is supplied at storage time from the raw
payload's retrieval timestamp.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_serializer


class SeriesDefinition(BaseModel):
    """Catalog entry describing one macro time series."""

    model_config = ConfigDict(frozen=True)

    series_id: str
    provider: str
    name: str
    unit: str
    description: str = ""


class MacroObservationIn(BaseModel):
    """A normalized observation ready for bitemporal storage."""

    model_config = ConfigDict(frozen=True)

    series_id: str
    observation_date: date
    value: Decimal


class MacroObservationOut(BaseModel):
    """An observation as served to consumers (engines, API, analysts)."""

    series_id: str
    observation_date: date
    as_of: datetime
    value: Decimal

    @field_serializer("value")
    def serialize_value(self, value: Decimal) -> str:
        """Emit plain decimal strings without storage-scale trailing zeros."""
        return format(value.normalize(), "f")


class IngestionReport(BaseModel):
    """Result of one connector ingestion run."""

    provider: str
    dataset: str
    raw_payload_id: int
    raw_payload_reused: bool
    observations_parsed: int
    observations_inserted: int
    retrieved_at: datetime
