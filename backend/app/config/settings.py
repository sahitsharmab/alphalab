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
    db_port: int = 5432
    db_user: str = "alphalab"
    db_password: str = "alphalab"
    db_name: str = "alphalab"

    cors_origins: list[str] = ["http://localhost:3000"]

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
