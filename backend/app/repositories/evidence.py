"""Repository for evidence records and their entity links."""

from datetime import datetime

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.evidence_sources import require_source
from app.models.evidence import EvidenceEntity, EvidenceRecord
from app.schemas.evidence import (
    EntityRef,
    EntityType,
    EvidenceCategory,
    EvidenceRecordIn,
    EvidenceRecordOut,
    SourceType,
)

logger = structlog.get_logger(__name__)


class EvidenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_records(
        self,
        records: list[EvidenceRecordIn],
        retrieved_at: datetime,
        raw_payload_id: int | None,
    ) -> int:
        """Insert records not seen before (by source-scoped external id)."""
        if not records:
            return 0
        source_ids = {record.source_id for record in records}
        existing: set[tuple[str, str]] = set()
        rows = await self._session.execute(
            select(EvidenceRecord.source_id, EvidenceRecord.external_id).where(
                EvidenceRecord.source_id.in_(source_ids)
            )
        )
        existing = {(row.source_id, row.external_id) for row in rows}

        inserted = 0
        for record in records:
            if (record.source_id, record.external_id) in existing:
                continue
            source = require_source(record.source_id)
            row = EvidenceRecord(
                source_id=record.source_id,
                source_type=source.source_type,
                trust_level=source.trust_level,
                external_id=record.external_id,
                category=record.category,
                title=record.title,
                url=record.url,
                published_at=record.published_at,
                retrieved_at=retrieved_at,
                content=record.content,
                raw_payload_id=raw_payload_id,
                provider_metadata=dict(record.provider_metadata),
                entities=[
                    EvidenceEntity(
                        entity_type=entity.entity_type,
                        entity_key=entity.entity_key,
                        role=entity.role,
                    )
                    for entity in record.entities
                ],
            )
            self._session.add(row)
            inserted += 1
        await self._session.flush()
        logger.info(
            "evidence_records_upserted",
            parsed=len(records),
            inserted=inserted,
            sources=sorted(source_ids),
        )
        return inserted

    async def list_for_entity(
        self,
        entity_type: EntityType,
        entity_key: str,
        categories: list[EvidenceCategory] | None = None,
        min_trust: int | None = None,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[EvidenceRecordOut]:
        """Evidence linked to one entity, newest first."""
        query = (
            select(EvidenceRecord)
            .join(EvidenceEntity, EvidenceEntity.evidence_id == EvidenceRecord.id)
            .where(
                EvidenceEntity.entity_type == entity_type,
                EvidenceEntity.entity_key == entity_key,
            )
            .order_by(EvidenceRecord.published_at.desc())
            .limit(limit)
        )
        if categories:
            query = query.where(EvidenceRecord.category.in_(categories))
        if min_trust is not None:
            query = query.where(EvidenceRecord.trust_level >= min_trust)
        if since is not None:
            query = query.where(EvidenceRecord.published_at >= since)

        rows = await self._session.scalars(query)
        return [self._to_out(row) for row in rows]

    async def latest_retrieved_at(
        self, source_id: str, entity_type: EntityType, entity_key: str
    ) -> datetime | None:
        """Newest retrieval time for a source's evidence about one entity."""
        result: datetime | None = await self._session.scalar(
            select(func.max(EvidenceRecord.retrieved_at))
            .join(EvidenceEntity, EvidenceEntity.evidence_id == EvidenceRecord.id)
            .where(
                EvidenceRecord.source_id == source_id,
                EvidenceEntity.entity_type == entity_type,
                EvidenceEntity.entity_key == entity_key,
            )
        )
        return result

    @staticmethod
    def _to_out(row: EvidenceRecord) -> EvidenceRecordOut:
        source = require_source(row.source_id)
        return EvidenceRecordOut(
            id=row.id,
            source_id=row.source_id,
            source_name=source.name,
            source_type=SourceType(row.source_type),
            trust_level=row.trust_level,
            category=EvidenceCategory(row.category),
            title=row.title,
            url=row.url,
            published_at=row.published_at,
            retrieved_at=row.retrieved_at,
            content=row.content,
            entities=[
                EntityRef(
                    entity_type=EntityType(entity.entity_type),
                    entity_key=entity.entity_key,
                    role=entity.role,
                )
                for entity in row.entities
            ],
            provider_metadata=row.provider_metadata,
        )
