# TASKS.md

# AlphaLab Development Backlog

This file is the single source of truth for development.

Claude Code / Codex must read this document at the beginning of every coding session.

After every completed task:

* Update this file.
* Mark completed work.
* Add discovered subtasks.
* Record architectural decisions if necessary.
* Never remove completed tasks.
* Keep priorities current.

---

# Current Goal

**AlphaLab v0.1 — Investment Decision Support System** (ADR-009, 2026-07-12).

Enter a ticker → receive a complete, evidence-backed investment briefing.

Research comes before automation. Every sprint must deliver a usable feature.

The near-term filter for every task: *"Will this help me make a better investment decision on a stock I have already chosen to analyze?"*

---

# MVP Roadmap — Investment Briefing (v0.1)

The original phases below remain the long-term map; the MVP re-sequences their contents into briefing-driven sprints. Architecture is unchanged — each sprint is a vertical slice through the existing layers.

## Sprint A — Deterministic briefing core (NEXT)

Deliverable: `/briefing/{ticker}` page with Technical Overview, Macro Environment, and Historical Context — all deterministic, no LLM.

* [ ] A1. Yahoo Finance connector (daily OHLCV + basic quote/profile), recorded-fixture tests
* [ ] A2. Market normalization: OHLCV schema (bitemporal, corporate-action aware at minimum via adjusted close)
* [ ] A3. Market storage: hypertable + repositories (as-of reads, same rules as macro)
* [ ] A4. Feature functions (pure, versioned — ADR-008): returns, rolling volatility, EMA, RSI, ATR, drawdown, 52-week range, relative volume, beta vs SPY
* [ ] A5. Technical engine: deterministic trend/momentum/volatility summary with the numbers that justify each statement
* [ ] A6. Inflation engine (re-scoped from Phase 1): inflation level + 3m/12m trend classification feeding the Macro Environment section
* [ ] A7. Briefing assembly API: `GET /api/v1/briefing/{ticker}` returning structured sections + evidence; briefing persisted as a research artifact
* [ ] A8. Frontend ticker page: search box → briefing (price chart, technical summary, macro chip, historical stats)

## Sprint B — AI synthesis layer

Deliverable: briefing gains Executive Summary, Bull Case, Bear Case, Risk Assessment, Confidence (labeled as model self-assessment), and "Questions to ask before investing."

* [ ] B1. LLM Gateway (ADR-006): provider-agnostic, logged, cached, versioned prompts, structured outputs only
* [ ] B2. Briefing synthesizer: LLM reasons ONLY over the structured evidence payload from Sprint A; every claim cites its evidence
* [ ] B3. Decide default LLM provider/model (open question → ADR)

## Sprint C — Events & news

Deliverable: briefing gains Company News, Sector News, and Upcoming Catalysts.

* [ ] C1. Earnings calendar connector (next earnings date, past surprises)
* [ ] C2. Macro calendar (CPI prints, FOMC meetings)
* [ ] C3. Company news: RSS/press releases + SEC filings (8-K) connector, ticker tagging
* [ ] C4. Sector mapping + sector news rollup

## Sprint D — Positioning data (source-risk gated)

Deliverable: briefing gains Short Interest, Options Activity, Analyst Revisions — each item ships only if a reliable free source is verified (pre-task per connector, like Nowflation).

* [ ] D1. Short interest (verify source: FINRA/Yahoo)
* [ ] D2. Options snapshot: put/call ratio, IV vs HV, notable OI (verify source)
* [ ] D3. Analyst estimates & revisions (verify source)

## Sprint E — Portfolio context

Deliverable: briefing gains Portfolio Impact; AlphaLab knows what you hold.

* [ ] E1. Portfolio model: manual positions entry (design tables so multi-user scoping is a later migration, not a rewrite)
* [ ] E2. Portfolio impact section: existing exposure, correlation of candidate vs holdings, concentration, beta contribution
* [ ] E3. Dashboard: portfolio summary widget

Future (kept in mind for model design, NOT implemented now): thesis journal — why bought, targets, risks, past briefings linked to trades.

---

# Phase 0 — Foundation

Status: ✅ Complete (2026-07-11)

Objective

Create the project infrastructure required to support all future development.

## Sprint 0 (revised 2026-07-11 — see ADR-004..008)

Scope changes from original plan: Redis removed (ADR-007), authentication skipped (ADR-007), frontend reduced to a skeleton, CI/migrations/observability added.

### Documentation

* [x] 0.1 Apply architecture-review doc updates (ADRs, bitemporality, LLM gateway, naming fixes)

### Project Setup (ordered; dependencies in parentheses)

* [x] 0.2 Initialize repository: git, .gitignore, README.md, CHANGELOG.md, .env.example (0.1)
* [x] 0.3 Backend scaffold: Poetry, ruff, mypy (strict), pytest configuration (0.2)
* [x] 0.4 Core module: pydantic-settings configuration + structured logging (0.3) — base error types deferred until the first consumer (Phase 1 connectors)
* [x] 0.5 FastAPI app factory + /api/v1/health (liveness + DB readiness) + tests (0.4)
* [x] 0.6 Docker: backend Dockerfile, compose with Postgres+TimescaleDB, healthchecks (0.3)
* [x] 0.7 Database bootstrap: async SQLAlchemy engine, Alembic wired, Timescale extension migration (0.6)
* [x] 0.8 Frontend skeleton: Next.js + TypeScript, one page calling health endpoint, in compose (0.6)
* [x] 0.9 CI: GitHub Actions — ruff, mypy, pytest, frontend build (0.3)
* [x] 0.10 Session close-out: docs updated, deliverable verified end-to-end (all)

Deferred (needs a consumer first): Redis, authentication, event bus, feature materialization.

---

### Deliverable

`docker compose up` starts backend + database + frontend skeleton.

`/api/v1/health` returns status including a real database connectivity check.

CI runs lint + typecheck + tests on every push.

No business logic yet.

---

# Phase 1 — Macro Intelligence MVP

Status: 🟡 In Progress (first vertical slice shipped 2026-07-11; remaining items re-sequenced into the MVP sprints above — inflation engine → Sprint A6, FRED/Treasury/BLS + rates → after Sprint C, AI summaries → Sprint B)

Priority: ⭐⭐⭐⭐⭐

Goal

Build the first complete vertical slice.

The objective is to transform public macroeconomic data into useful investment intelligence.

---

## Connectors

Order (approved 2026-07-11): Nowflation first for immediate user value and an end-to-end architecture demonstration; FRED, Treasury, BLS follow as complementary macro connectors.

* [x] Verify Nowflation API availability, stability, and licensing (2026-07-11: CSV exports open, no key/rate limits; no explicit license — personal use OK, revisit before redistribution)
* [x] Nowflation Connector (headline gauge; components dataset is a follow-up)
* [ ] Nowflation components dataset (per-component inflation, ~2.5MB CSV)
* [ ] FRED Connector (use ALFRED vintages — validates the bitemporal model, ADR-004)
* [ ] Treasury Connector
* [ ] BLS Connector
* [ ] Scheduler: daily automatic ingestion (manual POST endpoint exists)

---

## Normalization

* [x] Macro schema (bitemporal: observation_date + as_of, ADR-004) — MacroObservationIn/Out, series catalog
* [x] Inflation schema (Nowflation headline: index, yoy, coverage series)
* [ ] Rates schema

---

## Storage

* [x] Raw macro tables (immutable raw_payloads, content-hash deduplicated)
* [x] Normalized macro tables (bitemporal macro_observations hypertable + macro_series catalog)
* [ ] Data quality checks (gap detection, staleness, outlier flags)

---

## Macro Engine

* [ ] Inflation engine
* [ ] Interest rate engine
* [ ] Liquidity engine
* [ ] Macro regime classifier

---

## AI

* [ ] Daily macro summary
* [ ] Weekly macro report
* [ ] Macro analyst

---

## Dashboard

* [x] Inflation (KPI tiles: YoY, index, coverage; 2026-07-12)
* [ ] Rates
* [ ] Liquidity
* [x] Historical charts (YoY + index line charts, 90D/1Y/5Y/All ranges, as-of tooltips, data tables)
* [ ] AI summary

---

### Deliverable

Every morning AlphaLab should answer:

"What changed in the macro environment today?"

---

# Phase 2 — Market Intelligence MVP

Status: 🟡 Absorbed into MVP Sprint A (connector, OHLCV schema, storage, feature store) — the "research page per stock" deliverable becomes the briefing page.

Priority: ⭐⭐⭐⭐⭐

Goal

Create the market intelligence layer.

---

## Connectors

* [ ] Yahoo Finance

Future

* [ ] Polygon

---

## Normalization

* [ ] OHLCV schema
* [ ] Corporate actions schema

---

## Storage

* [ ] Market data tables

---

## Feature Store

* [ ] EMA
* [ ] SMA
* [ ] RSI
* [ ] ATR
* [ ] MACD
* [ ] VWAP
* [ ] Relative Volume
* [ ] Rolling Returns

---

## Dashboard

* [ ] Charts
* [ ] Indicators
* [ ] Watchlists

---

### Deliverable

Every stock should have a complete research page.

---

# Phase 3 — News Intelligence

Priority: ⭐⭐⭐⭐☆

---

## Connectors

* [ ] RSS
* [ ] SEC
* [ ] Company Press Releases

---

## Engine

* [ ] Event extraction
* [ ] Company tagging
* [ ] News classification

---

## AI

* [ ] News analyst
* [ ] Earnings summaries

---

### Deliverable

Every important news event should be summarized and linked to affected securities.

---

# Phase 4 — Research Platform

Priority: ⭐⭐⭐⭐⭐

This is the core of AlphaLab.

---

## Research

* [ ] Hypothesis model
* [ ] Experiment model
* [ ] Research notebook
* [ ] Knowledge base

---

## Backtesting

* [ ] Event-driven backtester
* [ ] Transaction costs
* [ ] Slippage
* [ ] Walk-forward validation
* [ ] Monte Carlo

---

### Deliverable

Users can create, test, save and compare research ideas.

---

# Phase 5 — AI Analysts

Priority: ⭐⭐⭐⭐☆

Build virtual analysts.

* [ ] Market Analyst
* [ ] Technical Analyst
* [ ] Macro Analyst
* [ ] News Analyst
* [ ] Portfolio Analyst
* [ ] Quant Analyst
* [ ] Risk Analyst
* [ ] Alpha Researcher

---

### Deliverable

Users can ask questions and receive evidence-backed answers.

---

# Phase 6 — Portfolio Intelligence

Priority: ⭐⭐⭐⭐☆

* [ ] Portfolio
* [ ] Performance
* [ ] Allocation
* [ ] Exposure
* [ ] Risk

---

### Deliverable

AlphaLab becomes the daily portfolio dashboard.

---

# Phase 7 — Paper Trading

Priority: ⭐⭐⭐☆☆

* [ ] Broker abstraction
* [ ] Paper broker
* [ ] Orders
* [ ] Positions
* [ ] Trade journal

---

### Deliverable

Paper trading powered by AlphaLab research.

---

# Phase 8 — Live Trading

Status: 🔒 Locked

This phase must not begin until:

* Research engine is stable.
* Backtests are statistically validated.
* Paper trading has demonstrated consistent performance over an extended evaluation period.
* Risk management has been thoroughly tested.

---

# Technical Debt

Claude/Codex should maintain this section.

None.

---

# Bugs

Claude/Codex should maintain this section.

None.

---

# Future Ideas

* Options analytics
* Insider trading
* Short interest
* Dark pools
* Factor investing
* Economic calendar
* Earnings calendar
* Strategy marketplace
* Mobile app
* Multi-user support

---

# Definition of Done

A task is complete only if:

* Architecture remains consistent.
* Code is production quality.
* Tests pass.
* Documentation is updated.
* TASKS.md is updated.
* No unnecessary technical debt is introduced.

Progress is measured by usable research capabilities, not by lines of code.
