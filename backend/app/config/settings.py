"""Typed application settings loaded from environment variables / .env files.

All configuration flows through this module (see ARCHITECTURE.md,
Cross-Cutting Concerns). Secrets are never hardcoded.
"""

from enum import StrEnum
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Deployment environment the application runs in."""

    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """AlphaLab backend settings.

    Every field can be overridden with an ``ALPHALAB_``-prefixed
    environment variable, e.g. ``ALPHALAB_DB_HOST``.
    """

    model_config = SettingsConfigDict(
        env_prefix="ALPHALAB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Environment = Environment.DEVELOPMENT
    log_level: str = "INFO"
    log_json: bool = False

    db_host: str = "localhost"
    # Host-side default matches docker-compose's published port (5433 to
    # avoid clashing with native PostgreSQL installs); inside the compose
    # network the backend overrides this with db:5432.
    db_port: int = 5433
    db_user: str = "alphalab"
    db_password: str = "alphalab"
    db_name: str = "alphalab"

    cors_origins: list[str] = ["http://localhost:3000"]

    # External providers
    nowflation_base_url: str = "https://nowflation.com"
    yahoo_base_url: str = "https://query1.finance.yahoo.com"
    yahoo_news_base_url: str = "https://feeds.finance.yahoo.com"
    federal_reserve_base_url: str = "https://www.federalreserve.gov"
    sec_data_base_url: str = "https://data.sec.gov"
    sec_www_base_url: str = "https://www.sec.gov"
    # SEC fair-access policy asks for contact info in the User-Agent —
    # override with your email via ALPHALAB_SEC_USER_AGENT.
    sec_user_agent: str = "AlphaLab/0.1 (personal research)"
    http_timeout_seconds: float = 30.0

    # Workspace
    benchmark_symbol: str = "SPY"
    # Re-fetch market history when the newest stored bar is older than this
    # (covers weekends + holidays without refetching every request).
    market_staleness_days: int = 4

    @property
    def database_url(self) -> str:
        """SQLAlchemy async connection URL for the primary database."""
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance (cached)."""
    return Settings()
