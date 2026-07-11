"""Market data ingestion: Yahoo → raw storage → normalization → bars."""

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.yahoo import YahooConnector
from app.normalization.yahoo import parse_chart
from app.repositories.macro import RawPayloadRepository
from app.repositories.market import InstrumentRepository, MarketBarRepository
from app.schemas.market import InstrumentInfo

logger = structlog.get_logger(__name__)


class MarketIngestionService:
    """Keeps an instrument's daily history present and fresh."""

    def __init__(
        self,
        session: AsyncSession,
        connector: YahooConnector,
        staleness_days: int = 4,
    ) -> None:
        self._session = session
        self._connector = connector
        self._staleness_days = staleness_days
        self._raw_payloads = RawPayloadRepository(session)
        self._instruments = InstrumentRepository(session)
        self._bars = MarketBarRepository(session)

    async def ensure_history(self, symbol: str, force: bool = False) -> InstrumentInfo:
        """Fetch and store history for ``symbol`` unless already fresh.

        Returns the instrument metadata (from storage when fresh, from the
        provider after a fetch). Does not commit — the caller owns the
        transaction boundary.
        """
        symbol = symbol.upper()
        if not force:
            latest = await self._bars.latest_bar_date(symbol)
            if latest is not None and latest >= (
                datetime.now(UTC).date() - timedelta(days=self._staleness_days)
            ):
                stored = await self._instruments.get(symbol)
                if stored is not None:
                    return InstrumentInfo(
                        symbol=stored.symbol,
                        name=stored.name,
                        currency=stored.currency,
                        exchange=stored.exchange,
                    )

        fetch = await self._connector.fetch_daily_history(symbol)
        instrument, bars = parse_chart(fetch.content)
        await self._instruments.upsert(instrument)
        raw_payload, _reused = await self._raw_payloads.store(
            provider=fetch.provider,
            dataset=f"{fetch.dataset}:{symbol}",
            source_url=fetch.url,
            content=fetch.content,
            content_hash=fetch.content_hash,
            retrieved_at=fetch.retrieved_at,
        )
        inserted = await self._bars.upsert_bars(
            bars, as_of=fetch.retrieved_at, raw_payload_id=raw_payload.id
        )
        logger.info(
            "market_history_ingested",
            symbol=symbol,
            bars_parsed=len(bars),
            bars_inserted=inserted,
        )
        return instrument
