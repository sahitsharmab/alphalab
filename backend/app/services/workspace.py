"""Assembles the Investment Workspace for a symbol (ADR-009/010).

Orchestration only: ensure data is present → run engines → assemble the
view → persist the snapshot as a research artifact.
"""

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.evidence import build_company_evidence_section
from app.engines.inflation import build_macro_section
from app.engines.technical import build_historical_section, build_technical_section
from app.models.research import WorkspaceSnapshot
from app.normalization.nowflation import SERIES_HEADLINE_YOY
from app.repositories.evidence import EvidenceRepository
from app.repositories.macro import MacroObservationRepository
from app.repositories.market import MarketBarRepository
from app.schemas.evidence import EntityType, EvidenceRecordOut
from app.schemas.workspace import PricePoint, QuoteSummary, WorkspaceView
from app.services.evidence_ingestion import EvidenceIngestionService
from app.services.market_ingestion import MarketIngestionService

logger = structlog.get_logger(__name__)


class WorkspaceError(Exception):
    """Raised when a workspace cannot be built for a symbol."""


class WorkspaceService:
    def __init__(
        self,
        session: AsyncSession,
        market: MarketIngestionService,
        evidence: EvidenceIngestionService | None = None,
        benchmark_symbol: str = "SPY",
    ) -> None:
        self._session = session
        self._market = market
        self._evidence_ingestion = evidence
        self._benchmark_symbol = benchmark_symbol.upper()
        self._bars = MarketBarRepository(session)
        self._macro = MacroObservationRepository(session)
        self._evidence = EvidenceRepository(session)

    async def build(self, symbol: str, force_refresh: bool = False) -> WorkspaceView:
        symbol = symbol.upper()
        instrument = await self._market.ensure_history(symbol, force=force_refresh)
        benchmark_bars = []
        if symbol != self._benchmark_symbol:
            await self._market.ensure_history(self._benchmark_symbol)
            benchmark_bars = await self._bars.get_bars(self._benchmark_symbol)

        bars = await self._bars.get_bars(symbol)
        if not bars:
            raise WorkspaceError(f"no price history available for {symbol}")
        yoy = await self._macro.get_observations(SERIES_HEADLINE_YOY)
        evidence_records = await self._load_evidence(symbol, force_refresh)

        sections = [
            build_technical_section(symbol, bars),
            build_historical_section(
                symbol,
                bars,
                benchmark_symbol=self._benchmark_symbol if benchmark_bars else None,
                benchmark_bars=benchmark_bars or None,
            ),
            build_company_evidence_section(evidence_records),
            build_macro_section(yoy),
        ]

        year_ago = datetime.now(UTC).date() - timedelta(days=366)
        price_history = [
            PricePoint(date=bar.bar_date, close=float(bar.adj_close))
            for bar in bars
            if bar.bar_date >= year_ago
        ]

        last = bars[-1]
        previous_close = float(bars[-2].adj_close) if len(bars) >= 2 else None
        quote = QuoteSummary(
            price=float(last.close),
            price_date=last.bar_date,
            change_1d=(float(last.adj_close) / previous_close - 1 if previous_close else None),
        )

        view = WorkspaceView(
            symbol=symbol,
            name=instrument.name,
            currency=instrument.currency,
            exchange=instrument.exchange,
            generated_at=datetime.now(UTC),
            quote=quote,
            price_history=price_history,
            sections=sections,
        )

        # Research is permanent: every generated workspace is kept.
        self._session.add(WorkspaceSnapshot(symbol=symbol, payload=view.model_dump(mode="json")))
        await self._session.commit()
        logger.info(
            "workspace_generated",
            symbol=symbol,
            sections=[s.id for s in sections],
            bars=len(bars),
        )
        return view

    async def _load_evidence(self, symbol: str, force_refresh: bool) -> list[EvidenceRecordOut]:
        """Ingest (best-effort) and load evidence records for the symbol.

        Evidence source outages must degrade the section, never break the
        workspace — failures are logged and the stored records still serve.
        """
        if self._evidence_ingestion is not None:
            for ingest in (
                self._evidence_ingestion.ensure_sec_filings,
                self._evidence_ingestion.ensure_ticker_news,
            ):
                try:
                    await ingest(symbol, force=force_refresh)
                except Exception as exc:
                    logger.warning(
                        "evidence_ingestion_degraded",
                        symbol=symbol,
                        step=ingest.__name__,
                        error=str(exc),
                    )
        return await self._evidence.list_for_entity(EntityType.INSTRUMENT, symbol, limit=30)
