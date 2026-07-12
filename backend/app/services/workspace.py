"""Assembles the Investment Workspace for a symbol (ADR-009/010).

Orchestration only: ensure data is present → run engines → assemble the
view → persist the snapshot as a research artifact.
"""

from datetime import UTC, date, datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.catalysts import build_catalysts_section
from app.engines.changes import build_what_changed_section
from app.engines.evidence import build_company_evidence_section
from app.engines.inflation import build_macro_section
from app.engines.relative import build_relative_section
from app.engines.technical import build_historical_section, build_technical_section
from app.features import technical as ft
from app.models.research import WorkspaceSnapshot
from app.normalization.nowflation import SERIES_HEADLINE_YOY
from app.repositories.calendar import CalendarEventRepository
from app.repositories.evidence import EvidenceRepository
from app.repositories.macro import MacroObservationRepository
from app.repositories.market import MarketBarRepository
from app.repositories.research import WorkspaceSnapshotRepository
from app.schemas.calendar import CalendarEventOut
from app.schemas.evidence import EntityType, EvidenceRecordOut
from app.schemas.market import MarketBarOut
from app.schemas.workspace import PricePoint, QuoteSummary, WorkspaceView
from app.services.calendar_ingestion import CalendarIngestionService
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
        calendar: CalendarIngestionService | None = None,
        benchmark_symbol: str = "SPY",
    ) -> None:
        self._session = session
        self._market = market
        self._evidence_ingestion = evidence
        self._calendar_ingestion = calendar
        self._benchmark_symbol = benchmark_symbol.upper()
        self._bars = MarketBarRepository(session)
        self._macro = MacroObservationRepository(session)
        self._evidence = EvidenceRepository(session)
        self._calendar = CalendarEventRepository(session)
        self._snapshots = WorkspaceSnapshotRepository(session)

    async def build(self, symbol: str, force_refresh: bool = False) -> WorkspaceView:
        symbol = symbol.upper()
        instrument = await self._market.ensure_history(symbol, force=force_refresh)
        context_bars: dict[str, list[MarketBarOut]] = {}
        for context_symbol in (self._benchmark_symbol, "QQQ"):
            if context_symbol == symbol or context_symbol in context_bars:
                continue
            await self._market.ensure_history(context_symbol)
            context_bars[context_symbol] = await self._bars.get_bars(context_symbol)
        benchmark_bars = context_bars.get(self._benchmark_symbol, [])

        bars = await self._bars.get_bars(symbol)
        if not bars:
            raise WorkspaceError(f"no price history available for {symbol}")
        yoy = await self._macro.get_observations(SERIES_HEADLINE_YOY)
        evidence_records = await self._load_evidence(symbol, force_refresh)
        today = datetime.now(UTC).date()
        calendar_events = await self._load_calendar(today, force_refresh)

        beta_1y: float | None = None
        if benchmark_bars:
            asset_by_date = {b.bar_date: float(b.adj_close) for b in bars}
            bench_by_date = {b.bar_date: float(b.adj_close) for b in benchmark_bars}
            beta_1y = ft.beta(asset_by_date, bench_by_date, 252)

        base_sections = [
            build_technical_section(symbol, bars),
            build_historical_section(
                symbol,
                bars,
                benchmark_symbol=self._benchmark_symbol if benchmark_bars else None,
                benchmark_bars=benchmark_bars or None,
            ),
            build_relative_section(symbol, bars, context_bars),
            build_company_evidence_section(evidence_records),
            build_catalysts_section(
                calendar_events,
                today,
                symbol=symbol,
                beta_1y=beta_1y,
                beta_benchmark=self._benchmark_symbol,
                beta_as_of=bars[-1].bar_date.isoformat(),
            ),
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
        previous_view = await self._snapshots.latest(symbol)
        sections = [
            build_what_changed_section(quote, base_sections, previous_view),
            *base_sections,
        ]

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

    async def _load_calendar(self, today: date, force_refresh: bool) -> list[CalendarEventOut]:
        """Ingest (best-effort) and load upcoming calendar events."""
        if self._calendar_ingestion is not None:
            for ensure in (
                self._calendar_ingestion.ensure_fed_calendar,
                self._calendar_ingestion.ensure_economic_releases,
            ):
                try:
                    await ensure(force=force_refresh)
                except Exception as exc:
                    logger.warning(
                        "calendar_ingestion_degraded", step=ensure.__name__, error=str(exc)
                    )
        return await self._calendar.list_upcoming(today, limit=60)
