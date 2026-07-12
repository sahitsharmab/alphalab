"""Evidence ingestion: SEC EDGAR → raw storage → normalization → evidence.

Freshness rule mirrors market ingestion: refetch when the newest stored
evidence for (source, symbol) is older than the staleness window.
"""

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.sec_edgar import SecEdgarConnector
from app.models.market import Instrument
from app.normalization import NormalizationError
from app.normalization.sec_edgar import parse_submissions, parse_ticker_map
from app.repositories.evidence import EvidenceRepository
from app.repositories.macro import RawPayloadRepository
from app.repositories.market import InstrumentRepository
from app.schemas.evidence import EntityType, EvidenceIngestionReport

logger = structlog.get_logger(__name__)

#: Evidence freshness window: EDGAR filings are event-driven, so a few
#: hours is plenty for a single-user platform without hammering SEC.
DEFAULT_STALENESS = timedelta(hours=6)


class UnknownSymbolError(Exception):
    """Raised when a symbol has no SEC CIK (not a US-listed filer)."""


class EvidenceIngestionService:
    def __init__(
        self,
        session: AsyncSession,
        connector: SecEdgarConnector,
        staleness: timedelta = DEFAULT_STALENESS,
    ) -> None:
        self._session = session
        self._connector = connector
        self._staleness = staleness
        self._evidence = EvidenceRepository(session)
        self._raw_payloads = RawPayloadRepository(session)
        self._instruments = InstrumentRepository(session)

    async def ensure_sec_filings(
        self, symbol: str, force: bool = False
    ) -> EvidenceIngestionReport | None:
        """Ingest SEC filings for ``symbol`` unless already fresh.

        Returns a report when a fetch happened, ``None`` when fresh. Does
        not commit — the caller owns the transaction boundary.
        """
        symbol = symbol.upper()
        if not force:
            newest = await self._evidence.latest_retrieved_at(
                "sec_edgar", EntityType.INSTRUMENT, symbol
            )
            if newest is not None and newest >= datetime.now(UTC) - self._staleness:
                return None

        cik = await self._resolve_cik(symbol)
        fetch = await self._connector.fetch_submissions(cik)
        raw_payload, _reused = await self._raw_payloads.store(
            provider=fetch.provider,
            dataset=f"{fetch.dataset}:{symbol}",
            source_url=fetch.url,
            content=fetch.content,
            content_hash=fetch.content_hash,
            retrieved_at=fetch.retrieved_at,
        )
        records = parse_submissions(fetch.content, symbol)
        inserted = await self._evidence.upsert_records(
            records, retrieved_at=fetch.retrieved_at, raw_payload_id=raw_payload.id
        )
        logger.info(
            "sec_filings_ingested",
            symbol=symbol,
            cik=cik,
            parsed=len(records),
            inserted=inserted,
        )
        return EvidenceIngestionReport(
            source_id="sec_edgar",
            symbol=symbol,
            records_parsed=len(records),
            records_inserted=inserted,
            retrieved_at=fetch.retrieved_at,
        )

    async def _resolve_cik(self, symbol: str) -> str:
        """CIK from the instrument catalog, else from SEC's official map."""
        instrument = await self._instruments.get(symbol)
        if instrument is not None and instrument.cik:
            return instrument.cik

        fetch = await self._connector.fetch_ticker_map()
        try:
            mapping = parse_ticker_map(fetch.content)
        except NormalizationError:
            raise
        cik = mapping.get(symbol)
        if cik is None:
            raise UnknownSymbolError(f"no SEC CIK found for symbol {symbol}")

        if instrument is not None:
            instrument.cik = cik
        else:
            # Evidence can be requested before market data: create a stub
            # catalog entry; the Yahoo connector enriches it later.
            self._session.add(
                Instrument(symbol=symbol, name=symbol, currency="", exchange="", cik=cik)
            )
        await self._session.flush()
        return cik
