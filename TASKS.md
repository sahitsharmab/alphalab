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

**AlphaLab v0.1 — Single-Stock Momentum Decision Workspace** (ADR-015, 2026-07-12).

Enter a ticker → evaluate the Weekly Thesis separately from today's Intraday Execution Context.

Research comes before automation. Every sprint must deliver a usable feature.

The near-term filter for every task: *"Will this help me make a better investment decision on a stock I have already chosen to analyze?"*

---

# MVP Roadmap — Investment Briefing (v0.1)

The original phases below remain the long-term map; the MVP re-sequences their contents into briefing-driven sprints. Architecture is unchanged — each sprint is a vertical slice through the existing layers.

## Momentum Roadmap — Approved 2026-07-12 (ADR-015)

### Sprint M1 — Intraday Market Foundation

* [x] M1a. **Twelve Data Basic SELECTED** for regular-session intraday (weekday verification 2026-07-13, `M1A_PROVIDER_SCORECARD.md`): ~44s bar delay, no in-progress bars, zero revisions, exact 5m aggregation (Sunday mismatch was a weekend artifact), 0 errors. Hard constraints for M1b+: regular session ONLY (no free pre/post), partial-venue labeling (~5% volume), ~1-min staleness, 8-credit/min budget.
* [ ] M1b. Canonical bitemporal one-minute storage with meaningful-change revisions and immutable raw references
* [ ] M1c. Deterministic five-minute aggregation; exchange-calendar session segmentation; previous-day, premarket, and configurable opening-range levels; feed-scoped VWAP
* [ ] M1d. Independent intraday bars/session APIs with freshness, delay, completed-bar, missing-bar, and coverage metadata
* [ ] M1e. One-session chart with extended-hours segmentation and persistent data-quality warnings

M1b–M1e may begin only after M1a selects a provider. No provider is selected as of 2026-07-12.

### Sprint M2 — Momentum and Relative Context

* [x] M2a. Daily momentum and relative context (2026-07-12): 9/21-day EMA distances, 1/5-day momentum, SPY and QQQ ETF-proxy relative returns over 1-week/1-month/3-month windows, deterministic relative-strength trend, and change since the immediately prior persisted workspace snapshot
* [ ] M2b. Intraday-only remainder after M1 ships: deterministic session structure and time-adjusted relative volume; sector/peer context remains blocked on Sprint C4 sector mapping and an explicit peer-universe design

### Sprint M3 — Risk Planner

* [x] M3. User entry/invalidation/target/risk inputs; deterministic position sizing, risk/reward, ATR/drawdown context, and catalyst/gap warnings (2026-07-12)

### Watchlist — User-Curated Momentum Overview

* [x] W1. Persist a user-selected ticker list with optional notes; show stored daily momentum, EMA9/21 distances, and one-month SPY/QQQ ETF-proxy relative returns without opaque ranking or automatic stock discovery (2026-07-12)

### Sprint M4 — Integrated Momentum Decision Workspace

* [ ] M4. Compose Weekly Thesis, Intraday Execution Context, evidence, catalysts, relative context, risk plan, bull/bear evidence, what changed, and missing information

## Sprint A — Deterministic workspace core ✅ Complete (2026-07-12)

Deliverable shipped: `/workspace/{ticker}` page (renamed per ADR-010) with Technical Overview, Historical Context, and Macro Environment — all deterministic, no LLM; every statement expandable to its evidence.

* [x] A1. Yahoo Finance connector (v8 chart API: daily OHLCV + adjusted close + instrument metadata)
* [x] A2. Market normalization: bitemporal OHLCV schema, exchange-timezone bar dating, adjusted close
* [x] A3. Market storage: instruments + market_bars hypertable + repositories (as-of reads, insert-on-change writes)
* [x] A4. Feature functions (pure, versioned — ADR-008): returns, realized vol, EMA, RSI, ATR, drawdown, 52-week range, relative volume, beta vs SPY
* [x] A5. Technical engine: statements + evidence (trend, momentum, volatility, volume) with degradation on short history
* [x] A6. Inflation engine: regime (low/moderate/high) + 3m trend classification feeding Macro Environment
* [x] A7. Workspace API: `GET /api/v1/workspace/{symbol}` (auto-ingests stale/missing history incl. benchmark; `?refresh=true`); every view persisted as a `workspace_snapshots` research artifact
* [x] A8. Frontend workspace page: ticker search → price chart + sections with expandable evidence tables

Follow-ups discovered:

* [ ] Workspace: earnings-date awareness (placeholder until Sprint C)
* [ ] Frontend component tests (scale/tick math, evidence rendering)
* [ ] Extract shared bitemporal repository helper if a third bitemporal table appears

## Sprint C — Evidence Foundation (reordered BEFORE Sprint B; ADR-011)

Deliverable: the workspace gains a **Company Evidence** section (SEC filings, press releases, quality headlines) — every item carrying source, category, and trust level. Evidence, not news.

* [x] C1. Source registry: configurable trust levels + source types (ADR-011) — `app/config/evidence_sources.py`
* [x] C2. EvidenceRecord model + storage + `evidence_entities` graph links (ADR-013) + repository (entity queries, source-scoped dedup)
* [x] C3. SEC EDGAR connector (Tier 1, trust 10): ticker→CIK via company_tickers.json, submissions JSON, deterministic 8-K item→category mapping, contact User-Agent (SEC 403s without one), `GET /api/v1/evidence/{symbol}` with category/trust/since filters — verified live (40 MU filings)
* [ ] C3-followup. Full filing text retrieval (records currently carry title/metadata/URL, not document text)
* [ ] C3-followup. Per-company EDGAR Atom feed polling for incremental updates (submissions JSON refetch is fine at current scale)
* [ ] C4. Sector mapping via SEC SIC codes (official, free) on the instruments catalog
* [x] C5. Press-release wires: pre-task verdict (2026-07-12) — per-company feeds are NOT free-viable (GlobeNewswire org URLs unguessable/general-feed trap, BusinessWire times out, PRNewswire aggregate-only). EDGAR 8-K remains the canonical company-statements channel (material PRs are filed as exhibits). Revisit if a stable per-company feed source appears.
* [x] C6 (re-scoped). Yahoo per-ticker news RSS connector (trust 7, media, role "mentioned") + generic safe RSS normalization (defusedxml). CNBC/MarketWatch general feeds deferred to a future market-context section (they are not per-company).
* [x] C7. Evidence Engine: deterministic Company Evidence section (filings summary, latest earnings filing, coverage with explicit trust framing); wired into the workspace with best-effort ingestion (source outages degrade, never break)
* [x] C8. Frontend: evidence tables now render links to originals + trust badges (provenance tooltip)

## Sprint C2 — Catalysts (Tier 3) ✅ Shipped 2026-07-12 (Fed calendar scope)

Deliverable shipped: workspace gains **Upcoming Catalysts** (FOMC decisions/minutes/press conferences, Beige Book, Fed data releases) from the Fed's official calendar JSON — verified, no key, trust 10.

* [x] C2-1. Fed calendar connector (`/json/calendar.json`, BOM + comma-day-list quirks handled), `calendar_events` storage (migration 0005), Catalysts engine + workspace section
* [x] C2-1b. Economic release dates via FRED release-dates API (owner's free key, 2026-07-12): CPI, PPI, Employment Situation, Advance Retail Sales, GDP, PCE (Personal Income & Outlays), UMich Surveys of Consumers — release ids verified live against `/fred/releases`; future dates confirmed. API key never enters stored URLs or logs. BLS HTML schedule rejected: aggressive bot-blocking (403s observed 2026-07-12).
* [x] C2-2. Earnings date: pre-task verdict — NO reliable free source (Yahoo quoteSummary needs crumb/cookie [401], Nasdaq API flaky). Gated out per ADR-009; the section states the gap honestly. Revisit candidates: company 8-K/PR announcements, FMP free tier w/ key.

## Sprint C3 — Catalyst Timeline ✅ Shipped 2026-07-12 (ADR-016)

Deliverable shipped: the catalysts section becomes a chronological **Catalyst Timeline** — economic releases + Fed events, each with an expandable playbook card (why it matters, transmission chain, watch list, conditional scenarios) from versioned editorial configuration, clearly separated from evidence.

* [x] C3-1. Catalyst playbook v1.0.0 (`app/config/catalyst_playbook.py`): 10 event kinds, editorial importance/scenarios/transmission, proxies labeled as proxies, no predictions
* [x] C3-2. `CatalystAssessment` on `Statement` (ADR-010 extension); timeline engine with beta-based relevance framing ("amplified/dampened") and per-event sensitivity honestly "not yet measured"
* [x] C3-3. Frontend playbook cards labeled "editorial assessment, not evidence"; FRED® attribution footer (API terms)
* [ ] C3-followup. Point-in-time event studies → measured per-event historical sensitivity (replaces "not yet measured")
* [ ] C3-followup. Decide whether the manual research packet should include playbook context (currently excluded to avoid steering the external model)

## Sprint B — AI synthesis layer (after Evidence Foundation)

Deliverable: workspace gains Executive Summary, Bull Case, Bear Case, Risk Assessment, Confidence (labeled as model self-assessment), and "Questions to ask before investing."

* [x] B-manual. Manual AI research packet (ADR-014): one-click copy of a versioned analysis prompt containing structured workspace statements, namespaced evidence citations, trust levels, and source URLs; no API key or LLM call (2026-07-12)
* [x] B-board. Decision Board (ADR-019, 2026-07-14) — deterministic Layer 1 of the reporting stack: `GET /api/v1/watchlist/board` + `/board` page composing each watchlist name's role (beta band), support/resistance bracket (nearest EMAs around price), momentum, relative strength, next market catalyst, and risk-plan presence. Facts only — the scenario-reasoning layer ("which name fits which CPI outcome") is B1/B2, gated on the LLM key.
* [ ] B0. Decide default LLM provider/model (open question → ADR); owner supplies API key
* [ ] B1. LLM Gateway (ADR-006): provider-agnostic, logged, cached, versioned prompts, structured outputs only
* [ ] B2. Workspace synthesizer: LLM reasons ONLY over structured evidence (Sprint A numbers + Sprint C records); every claim cites evidence with source + trust level

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

Future (kept in mind for model design, NOT implemented now):

* Thesis journal — why bought, targets, risks, past briefings linked to trades.
* **Decision Framework** (ADR-012) — configurable profiles combining standardized evidence signals per sector/asset class/market regime. Preserved contract: stable ids, source + trust on every evidence item, scores additive to (never replacing) evidence.
* Tier 4 community sentiment (Twitter/X, Reddit, Stocktwits) — explicitly out of scope for v0.1 (ADR-011).

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
* [ ] FRED Connector for observations (use ALFRED vintages — validates the bitemporal model, ADR-004). The release-dates slice shipped 2026-07-12 (Catalyst Timeline); the key is configured, so this is now unblocked.
* [ ] Treasury Connector
* [ ] BLS Connector
* [x] Scheduler: daily automatic ingestion for global datasets (Nowflation + Fed calendar + FRED release dates when the key is configured); ticker-scoped scheduling waits for a watchlist/universe (2026-07-12)

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
