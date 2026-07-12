# Architecture

## Overview

AlphaLab is a modular **Financial Intelligence Platform** designed to transform raw financial data into structured, explainable, and statistically validated research.

The platform is **not** centered around AI.

The platform is centered around **data, research, and evidence**.

AI is simply another consumer of that intelligence.

Every component has a single responsibility.

Every layer depends only on the layer immediately below it.

```
                         Applications

 ┌────────────────────────────────────────────────────────────┐
 │ Dashboard │ Portfolio │ Research │ API │ CLI │ Paper Trade │
 │ Future Trading Bot │ Mobile │ Alerts │ Reports │
 └────────────────────────────────────────────────────────────┘

                             ▲

                      AI Analyst Layer

 ┌────────────────────────────────────────────────────────────┐
 │ Market Analyst │ Technical Analyst │ Macro Analyst │
 │ News Analyst │ Quant Analyst │ Risk Analyst │
 │ Portfolio Analyst │ Alpha Researcher │
 └────────────────────────────────────────────────────────────┘

                             ▲

                    Research & Intelligence

 ┌────────────────────────────────────────────────────────────┐
 │ Research Engine │ Strategy Engine │
 │ Technical Engine │ Macro Engine │
 │ News Engine │ Fundamental Engine │
 │ Statistics Engine │ Risk Engine │
 │ Portfolio Engine │ Backtesting Engine │
 └────────────────────────────────────────────────────────────┘

                             ▲

                        Feature Store

 ┌────────────────────────────────────────────────────────────┐
 │ Technical Indicators │ Factors │ Volatility │
 │ Relative Strength │ Correlations │ Risk Metrics │
 │ Engineered Features │
 └────────────────────────────────────────────────────────────┘

                             ▲

                     Storage & Knowledge

 ┌────────────────────────────────────────────────────────────┐
 │ Raw Data │ Normalized Data │ Research │
 │ Portfolio │ Features │ Metadata │
 └────────────────────────────────────────────────────────────┘

                             ▲

                    Normalization Layer

 ┌────────────────────────────────────────────────────────────┐
 │ Market Schema │ Macro Schema │ News Schema │
 │ Fundamental Schema │ Event Schema │
 └────────────────────────────────────────────────────────────┘

                             ▲

                        Connectors

 ┌────────────────────────────────────────────────────────────┐
 │ Yahoo │ Nowflation │ FRED │ SEC │ RSS │
 │ Polygon │ FMP │ Treasury │ BLS │ ECB │
 └────────────────────────────────────────────────────────────┘
```

---

# Core Philosophy

Information always flows upward.

```
Connectors

↓

Normalization

↓

Storage

↓

Feature Store

↓

Intelligence Engines

↓

Research

↓

AI Analysts

↓

Applications
```

No layer may bypass another.

AI never talks directly to external APIs.

Applications never access raw data.

Every layer consumes standardized internal models.

---

# Folder Structure

```
backend/

    app/

        api/

        connectors/

        normalization/

        storage/

        features/

        engines/

        research/

        analysts/

        portfolio/

        backtesting/

        alerts/

        scheduler/

        database/

        repositories/

        models/

        schemas/

        services/

        config/

        utils/

    tests/

frontend/

docs/

scripts/

docker/
```

Notes:

* `tests/` lives beside `app/` (not inside it) so test code is never shipped with the application package.
* Folders are created when they gain their first real module — no empty placeholder packages.

---

# Connectors

Connectors are responsible only for retrieving data from external providers.

Examples

* Yahoo Finance
* Nowflation
* FRED
* SEC EDGAR
* RSS
* Polygon
* Financial Modeling Prep

Every connector implements:

```
fetch()

health()

metadata()
```

Responsibilities

* Download data
* Authenticate
* Retry requests
* Handle rate limits
* Return raw responses

Connectors never:

* Calculate indicators
* Perform AI analysis
* Modify business logic
* Store derived features

---

# Normalization Layer

Every external source has different formats.

The normalization layer converts all incoming data into AlphaLab's internal schemas.

Example

```
Yahoo

↓

MarketBar
```

```
Polygon

↓

MarketBar
```

```
Nowflation

↓

MacroObservation
```

Downstream systems should never know where data originated.

Changing providers should not require changing business logic.

---

# Storage Layer

Raw data is immutable.

Every record stores:

* Source
* Provider
* Timestamp
* Retrieval Time
* Version
* Metadata

Never overwrite raw data.

Derived data always references raw data.

## Bitemporal Model (ADR-004)

All normalized time-series data stores **two** time dimensions:

* `observation_date` — the period the value describes.
* `as_of` — the moment the value became knowable (publication time, or retrieval time if the provider exposes no vintage).

Revisions are new rows with a newer `as_of`. Nothing is updated in place.

The storage layer supports **as-of querying**: "give me this series as it was known on date X."

This is what makes backtests free of look-ahead bias and makes "data version" a cheap scalar (an as-of timestamp) instead of a snapshot.

---

# Feature Store

The Feature Store contains reusable engineered features.

Examples

Technical

* EMA
* SMA
* RSI
* ATR
* VWAP
* MACD
* Bollinger Bands
* ADX

Statistical

* Rolling Returns
* Rolling Volatility
* Correlation
* Beta
* Sharpe
* Sortino
* Drawdown

Market

* Relative Strength
* Relative Volume
* Gap %
* Trend Strength

Features are implemented as **pure, deterministic, versioned functions computed on demand** (ADR-008). Each feature implementation carries a version identifier recorded in experiment manifests.

Materialization/caching is introduced only when a measured latency problem appears; the pure-function layer then becomes the recompute backend.

---

# Intelligence Engines

Engines transform structured data into intelligence.

## Technical Engine

Produces

* Trend
* Momentum
* Support
* Resistance
* Patterns

## Macro Engine

Produces

* Inflation State
* Liquidity
* Interest Rate Environment
* Market Regime

## News Engine

Produces

* Company Events
* Earnings Events
* M&A
* Product Releases
* Sentiment

## Fundamental Engine

Produces

* Ratios
* Growth Metrics
* Valuation Metrics
* Financial Health

## Statistics Engine

Produces

* Performance Metrics
* Factor Analysis
* Correlations
* Significance Tests

## Risk Engine

Produces

* VaR
* Exposure
* Concentration
* Drawdown
* Correlation Risk

---

# Research Layer

The Research Layer is the heart of AlphaLab.

Everything eventually becomes research.

```
Question

↓

Hypothesis

↓

Experiment

↓

Backtest

↓

Validation

↓

Knowledge
```

Research is permanent.

Every experiment is reproducible.

Every conclusion references evidence.

Nothing is deleted.

## Experiment Manifest (ADR-005)

A reproducible run is defined by its manifest:

* Git commit SHA of the code
* Strategy/experiment configuration hash
* Data as-of timestamp per dataset consumed
* Random seeds
* Dependency lockfile hash
* Feature implementation versions

Two runs with identical manifests must produce identical results.

---

# Knowledge Base

Every experiment becomes part of the platform's institutional memory.

Each research record stores

* Question
* Hypothesis
* Data Version
* Strategy Version
* Results
* Statistical Validation
* Evidence
* Confidence
* Conclusion

The platform should continuously accumulate knowledge.

---

# AI Analysts

AI Analysts reason over structured intelligence.

They never consume raw APIs.

Examples

* Market Analyst
* Technical Analyst
* Macro Analyst
* News Analyst
* Quant Analyst
* Risk Analyst
* Portfolio Analyst
* Alpha Researcher

Every response should include

```
Summary

Evidence

Confidence

Supporting Factors

Contradicting Factors

Risks

Recommended Actions

Sources
```

## LLM Gateway (ADR-006)

All analyst LLM calls flow through a single provider-agnostic **LLM Gateway**:

* Logs every call: prompt version, model, tokens, cost, latency.
* Prompts are versioned configuration, never inline strings.
* Responses are enforced Pydantic schemas (structured output / tool use), never parsed prose.
* Responses are cached, keyed by content hash of (prompt version + model + input payload).
* Provider-sourced text (news, filings) is untrusted **data**, never instructions — delimited as data in prompts.
* LLM self-reported confidence is labeled as model self-assessment, never as a calibrated probability. Statistical confidence comes from the Statistics Engine.

No analyst may call an LLM SDK directly.

## Manual AI Research Packet (ADR-014)

Until the LLM Gateway has a funded provider, the workspace can export its
latest persisted snapshot as a deterministic, versioned research prompt for a
user-operated ChatGPT or Claude session. The packet contains structured
statements and namespaced evidence references, source URLs, trust levels, and
explicit injection-defense instructions. It performs no model call and creates
no AI-generated AlphaLab output. This is a manual transport over the existing
research artifact, not an exception to the future gateway requirement.

---

# Strategy Framework

Strategies are configuration-driven.

Every strategy defines

* Universe
* Features
* Entry Rules
* Exit Rules
* Risk Rules
* Holding Period

Strategies never contain:

* UI logic
* Database logic
* API calls

---

# Backtesting

Every backtest must record

* Strategy Version
* Data Version
* Feature Version
* Transaction Costs
* Slippage
* Universe
* Start Date
* End Date

Performance

* CAGR
* Sharpe
* Sortino
* Max Drawdown
* Win Rate
* Profit Factor

Every backtest must be reproducible.

---

# Portfolio Module

Responsible only for

* Positions
* Orders
* Transactions
* Cash
* Allocation
* Exposure
* Returns
* Risk

Nothing else.

---

# Alerts

Supported alerts

* Price
* Indicator
* Macro
* News
* Risk
* Portfolio
* Research

Alerts are event-driven.

---

# Scheduler

Responsible only for scheduling work.

Examples

* Connector synchronization
* Feature recomputation
* News ingestion
* Macro updates
* Backtests
* Daily reports

Business logic never belongs inside scheduled jobs.

The current single-process scheduler runs existing ingestion-service callbacks
immediately on backend startup and at a configurable fixed interval. Each job
owns a fresh database session, failures are isolated between jobs, and shutdown
cancels outstanding loops cleanly. Docker Compose enables a 24-hour interval.
Nowflation and the Federal Reserve calendar are global scheduled datasets;
ticker-scoped market/evidence ingestion remains on-request until a watchlist or
universe provides an explicit scheduling scope.

---

# API

REST-first.

WebSockets where appropriate.

Version every endpoint.

```
/api/v1/
```

Expose schemas.

Never expose database models.

## Momentum Workspace Boundary (ADR-015)

The v0.1 workspace has two independent data products:

* **Weekly Thesis** consumes the existing daily market, macro, evidence, and catalyst layers.
* **Intraday Execution Context** will consume a separately verified intraday feed through its own connector, normalization, storage, feature, and API path. A failure in this path must not break the Weekly Thesis workspace.

The daily decision-support slice remains inside the Weekly Thesis boundary:

* Relative Context is an engine over normalized daily bars for the selected symbol, SPY, and QQQ. SPY and QQQ are labeled ETF proxies, never sector or peer truth.
* What Changed is an engine over the current structured workspace and the immediately prior persisted workspace snapshot. It never re-queries providers and does not imply that two builds occurred on separate trading days.
* The Risk Planner consumes user-owned plan inputs plus stored daily bars and calendar events. Its persisted assessment is deterministic; it is not an order, strategy, or recommendation.
* The watchlist is application state defining a user-curated universe. Its overview service reads normalized stored bars and pure features; it does not call connectors, rank stocks, or execute refresh business logic.

Intraday source/feed identity, coverage scope, observation time, retrieval time, estimated delay, freshness, completeness, missing-bar count, and known limitations are first-class output fields. Bars from different providers must never be silently blended into one session. If M1a selects a provider, AlphaLab will store canonical one-minute bars bitemporally and derive five-minute bars through a pure versioned function.

---

# Database Organization

Separate storage into

* Raw
* Normalized
* Features
* Research
* Portfolio
* AI
* System

Avoid monolithic tables.

---

# Cross-Cutting Concerns

## Configuration & Secrets

* All configuration through typed `pydantic-settings` classes.
* Secrets (API keys) come from environment variables / `.env` files.
* `.env.example` is committed; real `.env` files never are.
* No hardcoded values, no magic numbers.

## Observability

* Structured logging (JSON-capable) throughout the backend.
* Every connector run, engine computation, and LLM call is logged with context.
* Correlation IDs flow through the layer stack.

## Database Migrations

* All schema changes go through Alembic migrations.
* No manual schema edits, ever.

## Security Posture (ADR-007)

* Single-user, localhost-first. No authentication for now.
* Revisit before any public deployment and before Phase 7 (broker credentials).
* Execution capability remains physically absent from the codebase until Phase 8 unlocks.

---

# Dependency Rules

Allowed

```
Connectors

↓

Normalization

↓

Storage

↓

Feature Store

↓

Engines

↓

Research

↓

AI Analysts

↓

API

↓

Applications
```

Forbidden

* Applications calling Connectors
* AI calling Connectors
* Research modifying raw data
* Connectors calling AI
* Circular dependencies

---

# Engineering Principles

Whenever implementing a feature ask:

1. Is this a Connector?
2. Is this Normalization?
3. Is this Storage?
4. Is this a Feature?
5. Is this an Engine?
6. Is this Research?
7. Is this an AI Analyst?
8. Is this an Application?

If the answer is unclear:

Stop.

Refactor.

Choose the correct abstraction before writing code.

Architecture is more important than implementation.
