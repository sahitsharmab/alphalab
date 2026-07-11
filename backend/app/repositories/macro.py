"""Repositories for raw payloads and bitemporal macro data.

Bitemporal write rule (ADR-004): a new row is inserted for
(series, observation_date) only when the value differs from the latest
known revision — re-ingesting unchanged data must not bloat the table.

Bitemporal read rule: queries return the latest revision per observation
date with ``as_of <= requested as-of`` (defaulting to "now", i.e. the
latest known values).
"""

from datetime import UTC, date, datetime
from decimal import Decimal

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.macro import MacroObservation, MacroSeries, RawPayload
from app.schemas.macro import MacroObservationIn, MacroObservationOut, SeriesDefinition

logger = structlog.get_logger(__name__)


class RawPayloadRepository:
    """Stores immutable raw connector responses, deduplicated by content."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def store(
        self,
        provider: str,
        dataset: str,
        source_url: str,
        content: str,
        content_hash: str,
        retrieved_at: datetime,
    ) -> tuple[RawPayload, bool]:
        """Insert the payload if its content is new.

        Returns ``(payload, reused)`` where ``reused`` is True when an
        identical payload was already stored.
        """
        existing = await self._session.scalar(
            select(RawPayload).where(
                RawPayload.provider == provider,
                RawPayload.dataset == dataset,
                RawPayload.content_hash == content_hash,
            )
        )
        if existing is not None:
            return existing, True

        payload = RawPayload(
            provider=provider,
            dataset=dataset,
            source_url=source_url,
            content_hash=content_hash,
            payload=content,
            retrieved_at=retrieved_at,
        )
        self._session.add(payload)
        await self._session.flush()
        return payload, False


class MacroSeriesRepository:
    """Catalog of macro series definitions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, definitions: tuple[SeriesDefinition, ...]) -> None:
        """Register series definitions, updating descriptive fields."""
        for definition in definitions:
            statement = (
                pg_insert(MacroSeries)
                .values(
                    series_id=definition.series_id,
                    provider=definition.provider,
                    name=definition.name,
                    unit=definition.unit,
                    description=definition.description,
                )
                .on_conflict_do_update(
                    index_elements=[MacroSeries.series_id],
                    set_={
                        "name": definition.name,
                        "unit": definition.unit,
                        "description": definition.description,
                    },
                )
            )
            await self._session.execute(statement)

    async def list_all(self) -> list[MacroSeries]:
        result = await self._session.scalars(select(MacroSeries).order_by(MacroSeries.series_id))
        return list(result)


class MacroObservationRepository:
    """Bitemporal reads and writes of macro observations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_observations(
        self,
        observations: list[MacroObservationIn],
        as_of: datetime,
        raw_payload_id: int | None,
    ) -> int:
        """Insert observations whose value is new or revised; return count."""
        if not observations:
            return 0

        series_ids = {observation.series_id for observation in observations}
        latest_values = await self._load_latest_values(series_ids)

        inserted = 0
        for observation in observations:
            key = (observation.series_id, observation.observation_date)
            if key in latest_values and latest_values[key] == observation.value:
                continue
            self._session.add(
                MacroObservation(
                    series_id=observation.series_id,
                    observation_date=observation.observation_date,
                    as_of=as_of,
                    value=observation.value,
                    raw_payload_id=raw_payload_id,
                )
            )
            inserted += 1
        await self._session.flush()
        logger.info(
            "macro_observations_upserted",
            parsed=len(observations),
            inserted=inserted,
            as_of=as_of.isoformat(),
        )
        return inserted

    async def _load_latest_values(self, series_ids: set[str]) -> dict[tuple[str, date], Decimal]:
        """Latest known value per (series, observation_date) for the given series."""
        latest_as_of = (
            select(
                MacroObservation.series_id,
                MacroObservation.observation_date,
                func.max(MacroObservation.as_of).label("max_as_of"),
            )
            .where(MacroObservation.series_id.in_(series_ids))
            .group_by(MacroObservation.series_id, MacroObservation.observation_date)
            .subquery()
        )
        rows = await self._session.execute(
            select(
                MacroObservation.series_id,
                MacroObservation.observation_date,
                MacroObservation.value,
            ).join(
                latest_as_of,
                (MacroObservation.series_id == latest_as_of.c.series_id)
                & (MacroObservation.observation_date == latest_as_of.c.observation_date)
                & (MacroObservation.as_of == latest_as_of.c.max_as_of),
            )
        )
        return {(row.series_id, row.observation_date): row.value for row in rows}

    async def get_observations(
        self,
        series_id: str,
        start: date | None = None,
        end: date | None = None,
        as_of: datetime | None = None,
    ) -> list[MacroObservationOut]:
        """Series values as known at ``as_of`` (default: latest known)."""
        effective_as_of = as_of or datetime.now(UTC)

        ranked = select(
            MacroObservation.series_id,
            MacroObservation.observation_date,
            MacroObservation.as_of,
            MacroObservation.value,
            func.row_number()
            .over(
                partition_by=MacroObservation.observation_date,
                order_by=MacroObservation.as_of.desc(),
            )
            .label("revision_rank"),
        ).where(
            MacroObservation.series_id == series_id,
            MacroObservation.as_of <= effective_as_of,
        )
        if start is not None:
            ranked = ranked.where(MacroObservation.observation_date >= start)
        if end is not None:
            ranked = ranked.where(MacroObservation.observation_date <= end)

        subquery = ranked.subquery()
        rows = await self._session.execute(
            select(
                subquery.c.series_id,
                subquery.c.observation_date,
                subquery.c.as_of,
                subquery.c.value,
            )
            .where(subquery.c.revision_rank == 1)
            .order_by(subquery.c.observation_date)
        )
        return [
            MacroObservationOut(
                series_id=row.series_id,
                observation_date=row.observation_date,
                as_of=row.as_of,
                value=row.value,
            )
            for row in rows
        ]
