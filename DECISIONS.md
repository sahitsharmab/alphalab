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

# Open Questions

Questions that have not yet been answered.

* Should vector search be introduced for research? (Defer; `pgvector` slots into existing Postgres when the knowledge base warrants semantic search.)
* Which LLM provider/model should the LLM Gateway default to? (Decide when the first analyst is built.)
* Nowflation: confirm API availability, stability, and licensing terms before Phase 1 connector work begins.

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
