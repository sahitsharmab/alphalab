# Changelog

All notable user-visible changes to AlphaLab are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Evidence API: `GET /api/v1/evidence/{symbol}` returns trust-labeled, categorized, entity-linked evidence records — starting with SEC EDGAR filings (10-K/10-Q/8-K and other material forms, auto-fetched and deterministically categorized). Filter by category, minimum trust level, and date.
- Investment Workspace: enter a ticker (search box on the dashboard) to open `/workspace/{symbol}` — a one-year price chart plus Technical Overview, Historical Context, and Macro Environment sections. Every statement is expandable to its evidence (metric, value, as-of date, source). Market history is fetched automatically from Yahoo Finance and stored bitemporally; every generated workspace is persisted as a research artifact.
- Macro dashboard: dark-themed frontend showing headline inflation KPIs (YoY with 30-day delta, index level, basket coverage), interactive YoY and index line charts with crosshair tooltips and keyboard navigation, date-range presets (90D/1Y/5Y/All), per-chart data tables, and an "Update data" button that triggers ingestion.
- Macro intelligence (first slice): Nowflation headline inflation gauge ingestion (`POST /api/v1/macro/ingest/nowflation`), series catalog (`GET /api/v1/macro/series`), and bitemporal observation queries (`GET /api/v1/macro/series/{id}/observations` with `start`/`end`/`as_of`) backed by an immutable raw-payload store and a TimescaleDB hypertable.
- Sprint 0 foundation: Dockerized backend (FastAPI) with `/api/v1/health` endpoint reporting database connectivity, PostgreSQL + TimescaleDB, and a minimal Next.js frontend that displays platform health.

### Changed

- Docker Compose now publishes the database on host port 5433 (was 5432) to avoid clashing with native PostgreSQL installations.
