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

Build the best free quantitative research platform possible.

Research comes before automation.

Every sprint must deliver a usable feature.

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

Priority: ⭐⭐⭐⭐⭐

Goal

Build the first complete vertical slice.

The objective is to transform public macroeconomic data into useful investment intelligence.

---

## Connectors

Order (approved 2026-07-11): Nowflation first for immediate user value and an end-to-end architecture demonstration; FRED, Treasury, BLS follow as complementary macro connectors.

* [ ] Verify Nowflation API availability, stability, and licensing (pre-task; fall back to FRED-first if unusable)
* [ ] Nowflation Connector
* [ ] FRED Connector (use ALFRED vintages — validates the bitemporal model, ADR-004)
* [ ] Treasury Connector
* [ ] BLS Connector

---

## Normalization

* [ ] Macro schema (bitemporal: observation_date + as_of, ADR-004)
* [ ] Inflation schema
* [ ] Rates schema

---

## Storage

* [ ] Raw macro tables
* [ ] Normalized macro tables (bitemporal)
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

* [ ] Inflation
* [ ] Rates
* [ ] Liquidity
* [ ] Historical charts
* [ ] AI summary

---

### Deliverable

Every morning AlphaLab should answer:

"What changed in the macro environment today?"

---

# Phase 2 — Market Intelligence MVP

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
