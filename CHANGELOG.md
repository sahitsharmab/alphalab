# Changelog

All notable user-visible changes to AlphaLab are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Daily momentum and relative context: Technical Overview now includes 9/21-day EMA distances and 1/5-day momentum; a new evidence-backed section compares the stock with SPY and QQQ (explicit ETF proxies) across 1-week, 1-month, and 3-month windows.
- What Changed Since the Previous Workspace: each build compares price, RSI, EMA distances, new company evidence, and new catalysts with the immediately prior persisted workspace snapshot.
- Deterministic Risk Planner: user-owned entry, invalidation, target, account size, and dollar-risk inputs produce position-size constraints, risk/reward, ATR/drawdown context, and catalyst warnings without issuing a trade recommendation.
- User-curated momentum watchlist: add stored tickers and notes, then compare daily returns, EMA distances, and one-month SPY/QQQ-relative context in a single overview.
- Catalyst Timeline: the workspace catalysts section is now a chronological timeline that includes official economic release dates (CPI, PPI, jobs report, retail sales, GDP, PCE, UMich sentiment) from the FRED release-dates API (free key), alongside Fed events. Each event carries an expandable playbook card — why it matters, the transmission chain to the stock, what to watch, and supportive/adverse conditional scenarios — clearly labeled as versioned editorial assessment, not evidence. The timeline is framed by the stock's measured 1-year beta vs SPY and honestly reports that per-event historical sensitivity is not yet measured.

- Manual AI research packet: copy a versioned, source-linked workspace prompt for analysis in ChatGPT or Claude without configuring or paying for an LLM API.

- Automatic daily ingestion for Nowflation and the Federal Reserve calendar, with an immediate refresh when the backend starts and configurable scheduling intervals.

- Upcoming Catalysts in the workspace: next FOMC rate decision (with press-conference note and days-away), FOMC minutes, Beige Book, and upcoming Federal Reserve data releases — sourced from the Fed's official calendar. Earnings dates are explicitly marked unavailable rather than guessed.
- Company Evidence in the workspace: every ticker page now shows SEC filings (with deterministic categories) and recent ticker coverage, each statement expandable to evidence rows with links to the original documents and source trust badges (10/10 filings vs 7/10 aggregated commentary, clearly framed).
- Evidence API: `GET /api/v1/evidence/{symbol}` returns trust-labeled, categorized, entity-linked evidence records — starting with SEC EDGAR filings (10-K/10-Q/8-K and other material forms, auto-fetched and deterministically categorized). Filter by category, minimum trust level, and date.
- Investment Workspace: enter a ticker (search box on the dashboard) to open `/workspace/{symbol}` — a one-year price chart plus Technical Overview, Historical Context, and Macro Environment sections. Every statement is expandable to its evidence (metric, value, as-of date, source). Market history is fetched automatically from Yahoo Finance and stored bitemporally; every generated workspace is persisted as a research artifact.
- Macro dashboard: dark-themed frontend showing headline inflation KPIs (YoY with 30-day delta, index level, basket coverage), interactive YoY and index line charts with crosshair tooltips and keyboard navigation, date-range presets (90D/1Y/5Y/All), per-chart data tables, and an "Update data" button that triggers ingestion.
- Macro intelligence (first slice): Nowflation headline inflation gauge ingestion (`POST /api/v1/macro/ingest/nowflation`), series catalog (`GET /api/v1/macro/series`), and bitemporal observation queries (`GET /api/v1/macro/series/{id}/observations` with `start`/`end`/`as_of`) backed by an immutable raw-payload store and a TimescaleDB hypertable.
- Sprint 0 foundation: Dockerized backend (FastAPI) with `/api/v1/health` endpoint reporting database connectivity, PostgreSQL + TimescaleDB, and a minimal Next.js frontend that displays platform health.

### Changed

- Docker Compose now publishes the database on host port 5433 (was 5432) to avoid clashing with native PostgreSQL installations.

### Fixed

- Garbled characters in the "Copy for ChatGPT / Claude" button states (mojibake from an earlier file-encoding incident).
