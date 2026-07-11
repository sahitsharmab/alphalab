"""Application factory and ASGI entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1.router import api_router
from app.config.logging import configure_logging
from app.config.settings import Settings, get_settings
from app.database.engine import create_engine, create_session_factory

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
    http_client = httpx.AsyncClient(timeout=settings.http_timeout_seconds)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logger.info("application_startup", environment=str(settings.env), version=__version__)
        yield
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
