"""Tests for typed settings."""

import pytest

from app.config.settings import Environment, Settings


def _clean_settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[call-arg]


def test_defaults_are_development() -> None:
    settings = _clean_settings()
    assert settings.env is Environment.DEVELOPMENT
    # Host-side default is 5433: compose publishes the DB there to avoid
    # colliding with native PostgreSQL installs on 5432.
    assert settings.db_port == 5433


def test_database_url_composition() -> None:
    settings = _clean_settings(
        db_user="u",
        db_password="p",
        db_host="h",
        db_port=5555,
        db_name="d",
    )
    assert settings.database_url == "postgresql+asyncpg://u:p@h:5555/d"


def test_environment_variables_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALPHALAB_ENV", "production")
    monkeypatch.setenv("ALPHALAB_DB_HOST", "db.internal")
    settings = _clean_settings()
    assert settings.env is Environment.PRODUCTION
    assert settings.db_host == "db.internal"
