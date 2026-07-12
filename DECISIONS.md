# DECISIONS.md

# AlphaLab Engineering Journal

This document is the institutional memory of AlphaLab.

Git history tells us **what changed**.

This document explains **why it changed**.

Every Claude Code / Codex session must update this document before finishing work.

---

# Purpose

The goals of this document are to:

* Record architectural decisions.
* Explain the reasoning behind decisions.
* Capture lessons learned.
* Document trade-offs.
* Track technical debt.
* Leave context for future development sessions.
* Allow a brand new engineer (human or AI) to immediately understand the project's evolution.

This document should grow continuously throughout the lifetime of AlphaLab.

Never delete previous entries.

---

# Decision Format

Every major architectural decision should use the following template.

```text
ADR-###

Title

Date

Status

Context

Problem

Options Considered

Decision

Reasoning

Consequences

Future Considerations
```

---

# Session Log Format

Every development session should append a new entry.

```text
Date

Goal

Completed

Challenges

Architectural Decisions

Technical Debt

Next Recommended Task

Notes
```

---

# Architecture Decision Records

---

## ADR-001

### Title

Research-Centric Architecture

### Date

2026-07-11

### Status

Accepted

### Context

The initial architecture considered placing AI at the center of the platform.

### Problem

Should AlphaLab be designed around AI or around quantitative research?

### Options Considered

Option 1

AI-first architecture.

Option 2

Research-first architecture.

### Decision

The platform will be research-centric.

AI becomes a consumer of structured intelligence rather than the core of the system.

### Reasoning

Research survives model changes.

AI models evolve rapidly.

Research methodology should remain stable regardless of the underlying LLM.

The value of AlphaLab comes from evidence and statistical validation, not AI-generated opinions.

### Consequences

All AI components consume structured internal data.

AI never directly communicates with external providers.

Research becomes the central abstraction throughout the system.

### Future Considerations

This decision should only be revisited if future architectures fundamentally change how intelligence systems operate.

---

## ADR-002

### Title

Connector-Based Data Architecture

### Date

2026-07-11

### Status

Accepted

### Context

The original architecture referred to external integrations as Providers.

### Problem

The term "Provider" created ambiguity between external services and our implementation.

### Decision

Use the term **Connector** for internal implementations.

Examples:

* YahooConnector
* NowflationConnector
* SECConnector

External services remain referred to as Providers.

### Reasoning

This separates responsibilities clearly.

Connectors are adapters.

Providers are external systems.

### Consequences

The naming convention is now consistent throughout the codebase.

---

## ADR-003

### Title

Best Source, Best Intelligence

### Date

2026-07-11

### Status

Accepted

### Context

Initially we discussed building many datasets ourselves.

### Decision

AlphaLab will integrate the highest-quality publicly available or official data sources whenever possible instead of recreating datasets.

Examples include:

* Nowflation
* FRED
* SEC EDGAR
* Yahoo Finance
* Treasury
* BLS

Engineering effort should focus on normalization, intelligence, and research rather than rebuilding existing datasets.

### Reasoning

The project's competitive advantage is interpretation and research, not raw data collection.

---

## ADR-004

### Title

Bitemporal Data Model for All Normalized Time-Series Data

### Date

2026-07-11

### Status

Accepted

### Context

Macroeconomic data is revised after initial publication (CPI, GDP, employment). Market data is rewritten by split/dividend adjustments. A backtest that uses final revised values is contaminated with look-ahead bias: it tests strategies against information that did not exist at decision time.

### Problem

How do we guarantee that every engine, backtest, and analyst can query data "as it was known" at any historical point in time?

### Options Considered

Option 1 — Single timestamp per observation (observation date only). Simple, but revisions silently overwrite history and look-ahead bias is undetectable.

Option 2 — Bitemporal model: every observation stores both the period it describes and the moment it became knowable.

Option 3 — Full snapshot copies of datasets per experiment. Correct but enormously wasteful and operationally painful.

### Decision

All normalized time-series records store two time dimensions:

* `observation_date` — the period the value describes.
* `as_of` — the moment the value became knowable (publication time, or retrieval time when the provider exposes no publication vintage).

Revisions are stored as new rows with a newer `as_of`. Nothing is updated in place.

The storage layer exposes as-of querying as a first-class capability: "give me the series as it was known on date X."

### Reasoning

Retrofitting bitemporality requires rewriting every schema, repository, and re-ingesting all data. Building it in from the start costs two columns and query discipline. FRED exposes true vintages (ALFRED); sources without vintages accumulate them naturally from retrieval time forward.

### Consequences

* Normalized schemas gain an `as_of` column and revision-aware unique constraints.
* Repositories default to "latest known" but always accept an as-of parameter.
* Backtests and experiments record the as-of timestamp they ran against, making "data version" a cheap scalar rather than a snapshot.

### Future Considerations

If a provider supplies full revision history, backfill vintages where available.

---

## ADR-005

### Title

Experiment Manifest — the Definition of Reproducibility

### Date

2026-07-11

### Status

Accepted

### Context

The documentation requires every backtest to record "Strategy Version, Data Version, Feature Version" without defining what a version is. Inconsistent versioning silently destroys reproducibility, the platform's core promise.

### Problem

What exactly must be recorded so that any experiment can be re-run and produce identical results?

### Decision

A reproducible run is defined by an **experiment manifest** containing:

* Git commit SHA of the code.
* Strategy/experiment configuration hash (canonical JSON of the config).
* Data as-of timestamp per dataset consumed (see ADR-004).
* Random seeds.
* Dependency lockfile hash.
* Feature implementation versions (see ADR-008).

Every research record and backtest stores its manifest. Two runs with identical manifests must produce identical results.

### Reasoning

With bitemporal storage, "data version" reduces to an as-of timestamp — no snapshot copies required. The manifest is a one-page contract that every future component implements consistently.

### Consequences

The Research layer (Phase 4) persists manifests with every experiment. Earlier phases already record `as_of` values, so nothing needs to be discarded later.

---

## ADR-006

### Title

LLM Gateway, Prompt Versioning, and Injection Defense

### Date

2026-07-11

### Status

Accepted

### Context

Eight AI analysts are planned. Without shared infrastructure they will be built eight different ways, and ADR-001's premise ("AI models evolve rapidly") demands the ability to swap providers cheaply.

### Problem

How do analysts call LLMs consistently, reproducibly, affordably, and safely?

### Decision

1. **Single LLM Gateway.** All analyst LLM calls go through one provider-agnostic gateway in the analysts layer. It logs every call: prompt version, model, tokens, cost, latency.
2. **Versioned prompts.** Prompts are configuration, not inline strings. Each prompt template has a version identifier recorded with every response.
3. **Structured outputs only.** Analyst responses are enforced Pydantic schemas (Summary, Evidence, Confidence, Supporting Factors, Contradicting Factors, Risks, Sources) via structured output / tool use — never parsed prose.
4. **Response caching.** Responses are cached keyed by content hash of (prompt version + model + input payload). This resolves the open question "Should AI responses be cached?" — yes.
5. **Injection defense.** All provider-sourced text (news, filings) is untrusted data, never instructions. It is delimited as data in prompts, and outputs are constrained to structured schemas.
6. **Calibration honesty.** LLM self-reported confidence is never displayed as a calibrated probability. It is labeled as model self-assessment; statistical confidence comes from the Statistics Engine.

### Consequences

Built when the first analyst is built (Phase 1 AI summary at the earliest). No analyst may call an LLM SDK directly.

---

## ADR-007

### Title

Single-User Platform Posture

### Date

2026-07-11

### Status

Accepted

### Context

AlphaLab is a personal research platform for one user, not a multi-tenant SaaS product.

### Decision

* **No authentication for now.** The platform is assumed to run on localhost / a trusted private network. Revisit before any public deployment and before Phase 7 (paper trading credentials).
* **No Redis** until a proven need exists (deferred from Sprint 0).
* **No event bus.** Event processing is synchronous until a real consumer requires otherwise. This resolves the open question "Should events be processed synchronously or through an event bus?"
* **TimescaleDB confirmed** as the primary storage engine (Postgres + hypertables covers all needs through Phase 6). This resolves the open question "Should TimescaleDB remain the primary storage engine?"

### Reasoning

Every deferred component can be added later at low cost (compose service, middleware). Building them now violates the project's own rule: never build infrastructure without an immediate consumer.

### Consequences

Sprint 0 scope shrinks: backend, database, Docker, minimal frontend, CI. Security posture is explicitly documented as "single-user, localhost-first."

---

## ADR-008

### Title

Feature Store as Pure Functions, Computed On Demand

### Date

2026-07-11

### Status

Accepted

### Context

The architecture describes features as "computed once, cached, and reused." Materialized caching hides the two hardest problems in feature engineering: cache invalidation (revised/late data silently invalidates downstream features) and feature versioning (a changed implementation leaves stale-but-plausible cached values — the worst failure mode).

### Decision

The Feature Store remains an architectural concept, but features are implemented as **pure, deterministic, versioned functions computed on read**. Each feature implementation carries a version identifier recorded in experiment manifests (ADR-005).

Materialization/caching is introduced only when a measured latency problem appears. The pure-function layer then becomes the recompute backend, so nothing is thrown away.

### Reasoning

At single-user scale, computing indicators over a few thousand bars takes milliseconds. Correctness during the research-building years outweighs redundant computation.

### Consequences

Phases 1–2 are simpler. Redis deferral (ADR-007) follows directly.

---

## ADR-009

### Title

AlphaLab v0.1 Is an Investment Decision Support System

### Date

2026-07-12

### Status

Accepted

### Context

The macro dashboard slice validated the architecture. The owner's investing style is discretionary: he already chooses which stock to analyze and does not need idea discovery. The highest-value near-term product is a complete, evidence-backed briefing for a chosen ticker.

### Problem

What should AlphaLab v0.1 optimize for, and does the architecture need to change?

### Options Considered

Option 1 — Continue the original phase order (macro → market → news → research platform), reaching a usable decision tool only after several horizontal phases.

Option 2 — Re-sequence implementation around one workflow: ticker → investment briefing. Each briefing section pulls a vertical slice through the existing layers.

### Decision

Option 2. AlphaLab v0.1 is an **Investment Decision Support System**: enter a ticker, receive a briefing (technicals, macro, news, catalysts, positioning, bull/bear, risks, portfolio impact, confidence, open questions).

The architecture is **unchanged** — connectors → normalization → storage → features → engines → research → AI analysts → applications. The pivot only reorders which connectors and engines are built first. Briefings are persisted as research artifacts (evidence-linked, versioned), consistent with "research is permanent."

A new product principle is added to PROJECT.md: AlphaLab teaches the user *how to think*, not *what to think* — evidence, reasoning, historical context, trade-offs, and uncertainty over binary buy/sell recommendations. The final decision always belongs to the user.

### Reasoning

* Every briefing section is a consumer path through existing layers; nothing about the layering, bitemporality, or research-centricity changes.
* The guiding filter ("will this help me make a better decision on a stock I already chose?") prevents horizontal infrastructure creep — consistent with the existing no-infrastructure-without-a-consumer rule.
* Persisting briefings from day one seeds the future memory capability (thesis journal, prior analyses, trades) without implementing it now.

### Consequences

* TASKS.md gains MVP Sprints A–E (deterministic briefing core → AI synthesis → events/news → positioning data → portfolio context).
* The inflation engine survives, re-scoped to feed the briefing's Macro Environment section (Sprint A6).
* Remaining Phase 1 connectors (FRED, Treasury, BLS) move after Sprint C.
* Positioning data (short interest, options, analyst revisions) is source-risk gated: each connector gets a Nowflation-style verification pre-task and ships only if a reliable free source exists.
* Single-user simplicity is reaffirmed (ADR-007); new tables are designed so multi-user scoping is a later migration, not a rewrite.

### Future Considerations

Idea discovery, screeners, and alpha research return to the roadmap after the decision-support loop is genuinely useful.

---

## ADR-010

### Title

Workspace, Not Report: Evidence Is a First-Class API Object

### Date

2026-07-12

### Status

Accepted

### Context

The v0.1 output was framed as an "investment briefing" — something you read. The owner's refinement: the page is an **Investment Workspace** — somewhere you think. Generated content is the starting point of an interactive research session; every conclusion must be traceable and explorable.

### Decision

1. The ticker page is the **Investment Workspace** (`/workspace/{symbol}`); naming follows throughout (API, UI, persistence).
2. The API contract makes evidence first-class: sections contain **statements**, and every statement carries machine-readable references to **evidence items** (metric, value, as-of, source). The UI renders statements expandable to their evidence.
3. Workspace snapshots are persisted as research artifacts, seeding the future thesis-journal/memory capability.

### Reasoning

Structuring output as statements-with-evidence costs almost nothing at build time but makes explorability the default contract — retrofitting traceability onto prose sections later would require rewriting every engine. This is the same lesson as bitemporality (ADR-004): encode the invariant in the data shape from day one.

### Consequences

Engines return structured statements + evidence, never prose blobs. Future interactive capabilities (drill-downs, notes, follow-up questions) attach to statements and evidence items without breaking the contract.

---

## ADR-011

### Title

Evidence, Not News: the EvidenceRecord Model, Trust Levels, and Source Tiers

### Date

2026-07-12

### Status

Accepted

### Context

The original roadmap framed Phase 3 as "News Intelligence." The owner's refinement: AlphaLab thinks in **evidence**, not news. The goal is the highest-quality evidence that could influence a decision, not the most headlines. v0.1 constraint: free sources only — official APIs and RSS preferred; reliability over completeness.

### Decision

1. **EvidenceRecord** replaces any "news" model as the normalized unit for all document-like evidence (filings, press releases, articles, economic releases). Fields: source, source_type, trust_level, published_at, retrieved_at, tickers, sector, category, url, title, normalized content, raw_payload reference (originals live in the existing immutable `raw_payloads` store), content_hash, provider metadata. Bitemporality (ADR-004) maps naturally: `published_at` is the knowledge time.
2. **Trust levels** are a property of the **source registry**, not per-item AI output and not hardcoded per item. A configurable registry assigns each source a trust level (10 = SEC EDGAR/Fed/Treasury/BLS/company IR, 9 = FRED/Nowflation, 8 = CNBC/MarketWatch, ≤5 = blogs/social). Denormalized onto each record at ingestion for querying.
3. **Trust measures provenance, not truth.** A 10/10 company press release is *authentically from the company*, not *objectively correct* — promotional bias is an interpretation problem for engines/AI, and high-trust content is still untrusted *instruction-wise* (prompt-injection rules of ADR-006 apply regardless of trust).
4. **Source tiers set implementation order:** Tier 1 official (SEC EDGAR, press-release wires, Fed, Treasury, BLS, FRED, Nowflation) → Tier 2 quality financial RSS (CNBC, MarketWatch; Reuters public RSS no longer exists — verified 2026-07-12) → Tier 3 calendars (official release schedules preferred over third-party calendars) → Tier 4 social sentiment (explicitly out of scope for v0.1).
5. **Free-only constraint** for v0.1; the connector abstraction is unchanged, so premium providers slot in later without architectural change.
6. **Naming**: stored documents are `EvidenceRecord`s; the workspace API's citation objects remain `EvidenceItem`s (a rendered reference — soon able to point at an EvidenceRecord).

### Reasoning

Evidence-first keeps the platform aligned with "evidence before opinion." A source registry makes trust configurable and auditable. Verified availability (2026-07-12): SEC EDGAR submissions JSON + full-text search + per-company Atom feeds, Fed press RSS, Treasury FiscalData API, PRNewswire RSS, CNBC RSS, MarketWatch RSS all live; Reuters RSS dead; Nasdaq earnings API flaky; FRED requires a free API key.

### Consequences

Sprint C becomes the Evidence Foundation sprint (EvidenceRecord model + Tier 1 connectors), and it moves **ahead of Sprint B (LLM synthesis)** — synthesis is only as good as the evidence beneath it, and this also unblocks work while the LLM provider decision is pending.

---

## ADR-012

### Title

Decision Framework: Preserve the Contract, Defer the Engine

### Date

2026-07-12

### Status

Accepted (direction; no implementation)

### Context

Not all evidence matters equally for every asset: semiconductors lean on technicals/news/options; utilities on macro/rates; biotech on regulatory events and cash runway. The owner wants this capability named **Decision Framework** (a product capability answering *what evidence matters, how much, why, and under which regime*), not "weighting" (an implementation detail).

### Decision

No weighting engine now. Evidence is presented independently. What we preserve **today** so the framework can arrive later without rework:

1. Sections, statements, and evidence carry **stable ids** and machine-readable values (already true since ADR-010).
2. Every evidence item/record carries **source and trust level** (ADR-011).
3. Engines may later expose **standardized signal scores** alongside statements; the schema treats scores as additive fields, never replacements for evidence.
4. Future **decision profiles** (per sector/asset class/market regime) are configuration that combines those scores — pure consumers of the existing contract.

### Reasoning

The expensive part of a weighting system is retrofitting traceable, scored, source-attributed evidence. That shape is being built anyway. The cheap part — the combining function — can wait until there is enough evidence variety for weights to mean something.

### Consequences

A "Decision Framework" phase is added to the long-term roadmap. Nothing else changes now.

---

## ADR-013

### Title

AlphaLab Is an Evidence Engine; Evidence Is Graph-Ready

### Date

2026-07-12

### Status

Accepted

### Context

Three refinements from the owner, approved 2026-07-12:

1. The deepest abstraction of the platform is an **Evidence Engine**. Dashboards, workspaces, AI analysts, research notebooks, and the future portfolio manager are all *views over the same evidence*.
2. Evidence should evolve toward an **Evidence Graph**: records reference normalized entities (companies, sectors, products, technologies, indicators, events, people) so future versions can connect information across sources without redesigning the data model. No graph database — relational tables and keys suffice.
3. Connectors should be able to expose **quality metadata** (trust, freshness, latency, coverage) so downstream systems can reason about evidence quality independently of content.

### Decision

1. `EvidenceRecord` is never an isolated document: an `evidence_entities` join table links every record to typed entities via `(entity_type, entity_key)` — e.g. (instrument, "MU"), (sector, SIC "3674"), (indicator, "cpi"). Entity *master* tables are added per type when a consumer needs them (instruments already exists); until then, `entity_key` is a well-defined soft reference. This is the minimal relational form of a graph edge, upgradeable later without breaking the model.
2. The connector contract keeps `metadata()`/`health()` as the seam for quality reporting; trust and source type come from the source registry (ADR-011), and freshness/latency/coverage metrics attach to these existing structures when a consumer (the Decision Framework, ADR-012) needs them.
3. The Evidence Engine framing is recorded in PROJECT.md as the platform's core abstraction. It does not change the layered architecture — it names what the layers exist to serve.

### Reasoning

The cost of graph-readiness today is one join table. The cost of retrofitting entity links onto millions of isolated documents later is a re-ingestion campaign. Same logic as ADR-004 and ADR-010: encode the invariant in the data shape while data volume is zero.

### Consequences

Sprint C's evidence storage ships with `evidence_entities` from day one. Queries like "all evidence touching MU" are entity-link queries, not text searches.

---

# Session Journal

---

## Session 001

### Date

2026-07-11

### Goal

Define the long-term vision and engineering architecture of AlphaLab.

### Completed

* Defined project vision.
* Created PROJECT.md.
* Created ARCHITECTURE.md.
* Designed layered architecture.
* Defined Data Acquisition Philosophy.
* Created TASKS.md.
* Established documentation workflow.

### Challenges

Determining whether AI or research should become the core abstraction.

Determining whether external integrations should be modeled as Providers or Connectors.

### Decisions

Adopted a research-centric architecture.

Introduced Connectors and a dedicated Normalization Layer.

Separated AI from data ingestion.

Introduced the Feature Store.

Established vertical-slice development.

### Technical Debt

None.

### Next Recommended Task

Initialize the repository and complete Sprint 0 (Foundation).

### Notes

The platform has evolved from the concept of an AI trading bot into an AI-powered Financial Intelligence Platform.

Trading automation remains intentionally out of scope until the research platform has matured.

---

## Session 002

### Date

2026-07-11

### Goal

Architecture review of the initial design, followed by Sprint 0 (Foundation) implementation.

### Completed

* Principal-level architecture review; findings approved by the owner with modifications (single-user posture, no auth, no Redis, keep folder structure, features on demand, Nowflation-first Phase 1).
* ADR-004 (bitemporal data model), ADR-005 (experiment manifest), ADR-006 (LLM gateway), ADR-007 (single-user posture), ADR-008 (features on demand).
* Updated ARCHITECTURE.md (bitemporality, LLM gateway, cross-cutting concerns), PROJECT.md (Connector naming per ADR-002), TASKS.md (revised Sprint 0, reordered Phase 1).
* Sprint 0 implemented end-to-end: FastAPI backend with typed settings (pydantic-settings), structured logging (structlog), async SQLAlchemy + Alembic + TimescaleDB extension migration, `/api/v1/health` with DB readiness, pytest suite (6 tests), ruff + mypy strict clean, minimal Next.js frontend showing platform health, Docker Compose stack, GitHub Actions CI.
* Created private GitHub repository `sahitsharmab/alphalab` and pushed `main`.

### Challenges

* Local machine had no Poetry (installed via pip) and Docker Desktop was stopped (started for end-to-end verification).
* A stray package-lock.json in the user home directory confused Next.js workspace-root inference; pinned `outputFileTracingRoot`.

### Architectural Decisions

See ADR-004 through ADR-008.

### Technical Debt

* Frontend Docker image runs `next dev` (dev server) rather than a production build. Acceptable for a single-user local platform; revisit if the frontend is ever deployed.
* Base error-type hierarchy deferred until the first consumer (Phase 1 connectors) exists.

### Next Recommended Task

Phase 1, first vertical slice: verify Nowflation API availability/licensing (pre-task), then Nowflation connector → macro normalization (bitemporal schema per ADR-004) → storage → inflation engine → dashboard.

### Notes

Commit messages must not include AI attribution lines (owner instruction, recorded in AGENTS.md Git Workflow).

---

## Session 003

### Date

2026-07-11

### Goal

Phase 1 first vertical slice: Nowflation → normalization → bitemporal storage → API.

### Completed

* Pre-task: verified Nowflation. CSV export endpoints are open (no key, no advertised rate limits): `/api/inflation/export/headline.csv` (daily gauge since 2018: date, index_value, yoy fraction, coverage_pct fraction) and `components.csv`. The dashboard's JSON endpoints 404 outside the browser and are undocumented — the connector uses only CSV exports. No explicit license text; site is promoted as Open Data. Personal research use OK; revisit before any redistribution.
* Connector layer: `BaseConnector` (metadata/health contract, retry with exponential backoff on 429/5xx/transport errors) + `NowflationConnector`.
* Normalization: headline CSV → three series (`nowflation.headline.index|yoy|coverage`); empty cells skipped, malformed rows fail loudly.
* Storage: immutable `raw_payloads` (content-hash dedup), `macro_series` catalog, bitemporal `macro_observations` TimescaleDB hypertable (PK series_id+observation_date+as_of, 1-year chunks). Migration 0002.
* Repositories with the bitemporal write rule (insert only new/changed values) and as-of reads (latest revision per date with as_of <= requested).
* `MacroIngestionService` orchestrating the slice in one transaction; API: GET /macro/series, GET /macro/series/{id}/observations (start/end/as_of), POST /macro/ingest/nowflation.
* Tests: 20 passing — connector (mock transport, retry/fatal paths), normalization, and 3 integration tests against a real TimescaleDB (fresh `alphalab_test` DB per run) covering ingest, idempotency, and as-of revision queries. CI now runs a TimescaleDB service with ALPHALAB_REQUIRE_DB=1.
* Live verification: ingested 8,971 real observations; re-ingest inserted 0 (idempotent); as-of stamps correct.
* Git workflow decision: solo development commits directly to main (CI on every push); PRs deferred until a second contributor or riskier changes warrant branches.

### Challenges

* A native PostgreSQL service on the host already listens on 5432, shadowing Docker's published port. Compose now publishes the DB on host port 5433 (container-internal stays 5432).
* `Numeric(20,8)` serialized with trailing zeros; API now emits normalized plain decimal strings.

### Technical Debt

* Ingestion is manual (POST endpoint); scheduler pending.
* `health()` on the Nowflation connector downloads the full headline CSV (~100KB) — cheap but not free; consider a lighter probe if it ever matters.

### Next Recommended Task

Macro dashboard slice (frontend chart of headline index/yoy consuming the observations API), then the inflation engine (regime classification) and FRED connector with ALFRED vintages.

### Notes

`as_of` for Nowflation = retrieval time (no publication vintages exposed). True vintage accumulation begins with our own repeated ingestion runs.

---

## Session 004

### Date

2026-07-12

### Goal

Macro dashboard slice: visualize the Nowflation headline gauge in the frontend.

### Completed

* Decision: solo development commits directly to `main` (no PRs) with CI as the gate; revisit when a second contributor or risky branches appear.
* Frontend dashboard (dark theme): KPI stat tiles (YoY with 30-day delta, index level, basket coverage), date-range presets (90D/1Y/5Y/All), two single-series line charts (YoY, index) with crosshair + tooltip, keyboard navigation (arrow keys), end-point direct labels, and collapsible data tables.
* Charts are a hand-rolled SVG `LineChart` component (no chart library): full control over mark specs, ~150 lines, zero dependencies.
* Series colors validated with the dataviz palette validator against the dark surface (#3987e5 / #199e70: CVD ΔE 69.8, contrast ≥3:1, all checks pass).
* Typed API client (`frontend/lib/api.ts`) — components never call fetch directly.
* Added root `.dockerignore` (the frontend build context was shipping 436MB of node_modules).
* Verified by headless-browser screenshots against the live backend (real ingested data): layout, hover layer, and tick formats eyeballed; two ambiguity fixes made ("Jul ’25" ticks, explicit "Data as of" format).

### Challenges

* Local port 3000/5433 coordination between compose containers and the dev server during verification.

### Technical Debt

* Frontend has no automated tests yet (build + typecheck only in CI). Add component tests when the frontend grows real logic (e.g., scale/tick math extraction).
* `playwright-core` added as a frontend devDependency for screenshot verification; harmless, used only locally.

### Next Recommended Task

Inflation engine (first Intelligence Engine): trend/regime classification over the gauge, exposed via API and a dashboard chip; then FRED connector with ALFRED vintages.

---

## Session 005

### Date

2026-07-12

### Goal

Roadmap refinement (ADR-009/010) and Sprint A: the deterministic Investment Workspace core.

### Completed

* ADR-009 (v0.1 = Investment Decision Support System) and ADR-010 (workspace framing; evidence as a first-class API object). PROJECT.md and TASKS.md updated accordingly.
* Yahoo connector (v8 chart API — verified: no key, browser UA required), normalization with exchange-timezone bar dating and adjusted closes, bitemporal `market_bars` hypertable + `instruments` catalog (migration 0003).
* Feature functions (pure, versioned): window returns, realized volatility, EMA, RSI (Wilder), ATR, max drawdown, 52-week range position, relative volume, OLS beta.
* Technical Engine + Inflation Engine emitting statements with first-class evidence (shared `_SectionBuilder` enforces id integrity; the `WorkspaceSection` validator makes untraceable claims unrepresentable).
* `WorkspaceService`: auto-ingests missing/stale history (symbol + SPY benchmark), assembles sections, persists every view to `workspace_snapshots` (research is permanent).
* API `GET /api/v1/workspace/{symbol}` with symbol validation, 404 for unknown tickers, `?refresh=true`.
* Frontend: `/workspace/[symbol]` page (price chart, sections with expandable evidence tables, refresh), ticker search on the dashboard.
* 45 backend tests passing (features known-values, engines, normalization, 4 workspace integration tests incl. ADR-010 traceability and snapshot persistence). Verified live: real MU workspace with 10y of bars; screenshots reviewed.

### Challenges

* Windows has no system IANA tz database — added `tzdata` dependency for `zoneinfo`.
* First beta tests used constant-growth series: zero return variance makes beta numerically undefined. Rewrote with varying-return series — a good reminder that statistical features need statistically meaningful test data.
* A PowerShell text replacement mangled UTF-8 (mojibake); recovered via cp1252 round-trip. Lesson: use Python for text surgery on UTF-8 files.

### Technical Debt

* Health endpoint doesn't yet report connector health (Yahoo/Nowflation probes exist but aren't wired in).
* `NowflationConnector.health()` and workspace auto-ingest fetch full history; fine at current scale.

### Next Recommended Task

Sprint B — LLM Gateway (ADR-006) + workspace synthesis: Executive Summary, Bull/Bear cases, Risks, Questions, reasoning only over Sprint A's evidence payload. Requires choosing the default LLM provider (open question).

### Notes

Sprint A guiding-question check: every item shipped serves "make a better decision on a stock I already chose."

---

## Session 006

### Date

2026-07-12

### Goal

Evidence-first refinement (ADR-011/012/013) and Sprint C tasks C1–C3.

### Completed

* ADR-011 (EvidenceRecord, provenance trust levels, source tiers, free-only), ADR-012 (Decision Framework: preserve the contract, defer the engine), ADR-013 (Evidence Engine framing; graph-ready evidence via `evidence_entities`).
* Source availability verification: EDGAR/Fed/Treasury/PRNewswire/CNBC/MarketWatch live; Reuters public RSS dead; Nasdaq earnings API flaky; FRED needs a free key.
* C1: source registry (`app/config/evidence_sources.py`) — trust measures provenance, never interpretive accuracy.
* C2: `evidence_records` + `evidence_entities` (migration 0004, also adds `instruments.cik`); repository with entity-linked queries, filters, and source-scoped external-id dedup.
* C3: SEC EDGAR connector (official endpoints only), deterministic form/8-K-item → category mapping (2.02→earnings, 5.02→press_release, …), insider Forms 3/4/5/144 excluded for v0.1; CIK resolution via the official ticker map with instrument-catalog caching; `GET /api/v1/evidence/{symbol}` with auto-ingest (6h staleness), category/min_trust/since filters.
* 54 backend tests passing; verified live: 40 real MU filings ingested, categorized, trust-labeled, entity-linked.

### Challenges

* SEC returns 403 for User-Agents without contact info — the UA is now configuration (`ALPHALAB_SEC_USER_AGENT`, flows through compose from .env; contact email never enters the repo).

### Technical Debt

* Evidence records carry title/metadata/URL but not full filing text (retrieval is a follow-up task).
* EDGAR refresh refetches the whole submissions JSON; per-company Atom feeds would be incremental (fine at current scale).

### Next Recommended Task

C5–C8: press-release wire connector (GlobeNewswire/BusinessWire pre-task), Tier 2 RSS (CNBC/MarketWatch), Evidence Engine + workspace "Company Evidence" section with trust badges. Then Sprint C2 (catalysts) and Sprint B (LLM synthesis).

### Notes

The platform's core abstraction is now named: AlphaLab is an Evidence Engine (ADR-013, PROJECT.md).

---

## Session 007

### Date

2026-07-12

### Goal

Sprint C completion (C5–C8): evidence sources + the workspace Company Evidence section.

### Completed

* Pre-task verdicts: per-company press-release wire feeds are not free-viable (GlobeNewswire per-org URLs are an unguessable/general-feed trap, BusinessWire times out, PRNewswire aggregate-only) — EDGAR 8-K stays the canonical company-statements channel. Yahoo per-ticker news RSS verified: relevant but commentary-heavy → trust 7, category market_news, entity role "mentioned".
* Generic RSS normalization with defusedxml (feeds are untrusted XML), YahooNewsConnector, registry entry.
* Evidence Engine (`engines/evidence.py`): deterministic Company Evidence section — filings summary (90-day window), latest earnings filing, coverage with explicit "aggregated commentary, not primary evidence" framing.
* Workspace integration: best-effort evidence ingestion (SEC + news) — source outages degrade the section, never break the workspace. `EvidenceItem` gained optional `trust_level` and `url` (additive per ADR-012).
* Frontend: evidence tables link to original documents and show trust badges.
* Evidence API now also ingests ticker news (separate `news_ingestion` report).
* 58 backend tests passing; verified live (MU: 3 filings/90d + 20 coverage items) and visually via screenshot.

### Challenges

* The GlobeNewswire probe returned HTTP 200 with the *general* wire feed for an invented per-org URL — a silent wrong-content trap; only item-level inspection caught it. Lesson: verify feed *content*, not just status codes.

### Technical Debt

* CNBC/MarketWatch general feeds deferred until a market-context (non-per-company) section exists.
* Yahoo news descriptions are stored raw; no relevance scoring yet (candidate for the Decision Framework era).

### Next Recommended Task

Sprint C2 (catalysts from official release schedules; earnings-date pre-task) or Sprint B (LLM Gateway + synthesis — needs the owner's provider decision and API key).

---

## Session 008

### Date

2026-07-12

### Goal

Sprint C2: Upcoming Catalysts in the workspace.

### Completed

* Pre-task verdicts: the Fed's `/json/calendar.json` is a first-class official source (no key; FOMC/Beige Book/stat releases; BOM + comma-day-list quirks). BLS HTML schedules 403 non-browser clients unpredictably — rejected; CPI/jobs/GDP dates will come from FRED's release-dates API once the owner registers a free key. Earnings dates: no reliable free source (Yahoo quoteSummary 401s without crumb; Nasdaq flaky) — gated out per ADR-009, stated honestly in the UI.
* FederalReserveConnector + normalization (event classification: FOMC meeting/minutes/press conference, Beige Book, stat releases; speeches/testimony excluded from catalysts), `calendar_events` table (migration 0005), repository, daily-staleness ingestion service.
* Catalysts Engine: next FOMC decision with days-away and same-day-press-conference note, minutes/Beige Book, upcoming Fed data releases, and explicit gap statements.
* Workspace gains the Upcoming Catalysts section (best-effort ingestion, degrades on outage).
* 62 backend tests; verified live (FOMC 2026-07-29 in 17 days; Beige Book in 3 days) and visually.

### Technical Debt

* Catalysts are macro-only until FRED (CPI/jobs/GDP) and an earnings-date source land.

### Next Recommended Task

Sprint B (LLM Gateway + synthesis — needs owner's provider decision + key) or C2-1b (FRED release dates — needs owner's free FRED key).

---

## Session 009

### Date

2026-07-12

### Goal

Implement the highest-value unblocked fallback because neither the LLM nor FRED API key was configured: automatic ingestion scheduling.

### Completed

* Added a small async periodic scheduler that runs jobs immediately and at a configurable interval, isolates failures, and shuts down cleanly.
* Wired global Nowflation and Federal Reserve calendar refreshes through their existing ingestion services; no connector, normalization, or storage logic lives in scheduled jobs.
* Enabled a 24-hour interval in Docker Compose while keeping library/test application factories opt-in.
* Added scheduler unit coverage and corrected a date-sensitive Yahoo test fixture whose UTC-midnight timestamps collided across the New York DST transition.
* 65 backend tests pass; ruff, formatting, and strict mypy are clean. Live container verification confirmed both jobs and a real MU workspace.

### Architectural Notes

An in-process scheduler is sufficient for the current single-process, single-user posture (ADR-007). If deployment gains multiple backend replicas, scheduling must move to one elected/dedicated process to avoid duplicate provider traffic. Ticker-scoped scheduling is intentionally deferred until a watchlist or explicit universe defines what to refresh.

### Next Recommended Task

Sprint B once the owner provides an actual provider/model selection and `ALPHALAB_LLM_API_KEY`; otherwise C2-1b once `ALPHALAB_FRED_API_KEY` is available.

---

# Open Questions

Questions that have not yet been answered.

* Should vector search be introduced for research? (Defer; `pgvector` slots into existing Postgres when the knowledge base warrants semantic search.)
* Which LLM provider/model should the LLM Gateway default to? (Decide when the first analyst is built.)

Resolved and moved into ADRs:

* TimescaleDB as primary storage engine → ADR-007 (yes).
* Synchronous events vs event bus → ADR-007 (synchronous).
* AI response caching → ADR-006 (yes, content-hash keyed).

Move questions into ADRs once decisions are made.

---

# Technical Debt

This section tracks intentional shortcuts.

Format

```text
ID

Description

Reason

Impact

Planned Resolution
```

Leave empty until required.

---

# Lessons Learned

Record important insights discovered during development.

Examples:

* Avoid premature optimization.
* Favor vertical slices over horizontal infrastructure.
* Normalize data immediately after ingestion.
* Preserve raw data permanently.
* AI should consume research, not create architecture.

This section should become more valuable over time than the code itself.
