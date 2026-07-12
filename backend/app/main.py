"""Application factory and ASGI entry point."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import timedelta

import httpx
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.api.v1.router import api_router
from app.config.logging import configure_logging
from app.config.settings import Settings, get_settings
from app.connectors.federal_reserve import FederalReserveConnector
from app.connectors.fred import FredConnector
from app.connectors.nowflation import NowflationConnector
from app.database.engine import create_engine, create_session_factory
from app.scheduler.periodic import PeriodicJob, PeriodicScheduler
from app.services.calendar_ingestion import CalendarIngestionService
from app.services.macro_ingestion import MacroIngestionService

logger = structlog.get_logger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build a fully configured FastAPI application.

    Accepting a ``Settings`` instance keeps the factory testable and free
    of global state; the default resolves from the environment.
    """
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_json)

    # Engine and client construction are lazy (no connection until first
    # use), so both are safe outside the lifespan; the lifespan owns cleanup.
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    http_client = httpx.AsyncClient(
        timeout=settings.http_timeout_seconds,
        # Some providers (Yahoo) reject default library user agents.
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AlphaLab/0.1"},
    )

    def ingestion_job(
        service_call: Callable[[AsyncSession], Awaitable[None]],
    ) -> Callable[[], Awaitable[None]]:
        async def run() -> None:
            async with session_factory() as session:
                await service_call(session)
                await session.commit()

        return run

    async def ingest_nowflation(session: AsyncSession) -> None:
        connector = NowflationConnector(http_client, settings.nowflation_base_url)
        await MacroIngestionService(session, connector).ingest_nowflation_headline()

    async def ingest_fed_calendar(session: AsyncSession) -> None:
        connector = FederalReserveConnector(http_client, settings.federal_reserve_base_url)
        await CalendarIngestionService(session, connector).ensure_fed_calendar()

    async def ingest_economic_releases(session: AsyncSession) -> None:
        fed = FederalReserveConnector(http_client, settings.federal_reserve_base_url)
        fred = FredConnector(http_client, settings.fred_api_key, settings.fred_base_url)
        await CalendarIngestionService(session, fed, fred=fred).ensure_economic_releases()

    interval = timedelta(hours=settings.scheduler_interval_hours)
    jobs = [
        PeriodicJob("nowflation_headline", interval, ingestion_job(ingest_nowflation)),
        PeriodicJob("fed_calendar", interval, ingestion_job(ingest_fed_calendar)),
    ]
    if settings.fred_api_key:
        jobs.append(
            PeriodicJob("fred_release_dates", interval, ingestion_job(ingest_economic_releases))
        )
    scheduler = PeriodicScheduler(tuple(jobs))

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logger.info("application_startup", environment=str(settings.env), version=__version__)
        if settings.scheduler_enabled:
            scheduler.start()
        try:
            yield
        finally:
            if settings.scheduler_enabled:
                await scheduler.stop()
            await http_client.aclose()
            await engine.dispose()
        logger.info("application_shutdown")

    app = FastAPI(
        title="AlphaLab",
        description="AI-powered Financial Intelligence Platform",
        version=__version__,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.http_client = http_client
    app.state.scheduler = scheduler

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    return app


app = create_app()
