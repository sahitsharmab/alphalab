# HANDOFF.md — Continuing AlphaLab Development

Purpose: let a new engineer (human, Codex, Claude, or any AI session with no
prior context) continue this project seamlessly. Read this file first, then
the project documents in this order:

1. AGENTS.md — your role, rules, and workflow
2. PROJECT.md — vision and philosophy (note "The Evidence Engine" and the v0.1 MVP section)
3. ARCHITECTURE.md — layers and dependency rules
4. DECISIONS.md — ADR-001..017 and the session journal (read the ADRs; skim the journal)
5. TASKS.md — the backlog; the "MVP Roadmap" section is the current plan

---

## Current State (2026-07-12, deterministic daily decision tools shipped; M1a still blocked on a weekday run)

Everything below is implemented, tested, verified live, and green in CI:

* **Sprint 0** — FastAPI backend, TimescaleDB, Alembic (7 migrations), Next.js frontend, Docker Compose, GitHub Actions CI.
* **Macro slice** — Nowflation connector → bitemporal `macro_observations` → `GET /api/v1/macro/...` → dashboard with charts (`frontend/app/page.tsx`).
* **Sprint A: Investment Workspace** — Yahoo connector → bitemporal `market_bars` → pure feature functions → Technical/Historical/Inflation engines → `GET /api/v1/workspace/{symbol}` → `/workspace/[symbol]` page. Every statement carries evidence ids; the `WorkspaceSection` validator rejects untraceable claims.
* **Sprint C2 (complete): Catalysts** — Fed calendar connector (`/json/calendar.json`, official, no key), `calendar_events` storage; earnings dates honestly gated out (no reliable free source).
* **Sprint C3 (complete): Catalyst Timeline (ADR-016)** — FRED release-dates connector (owner's free key in `.env` as `ALPHALAB_FRED_API_KEY`; the key must never appear in stored URLs or logs — the base connector's `params` mechanism and the quieted httpx logger exist for this). CPI/PPI/jobs/retail/GDP/PCE/UMich dates as `economic_release` events. The catalysts section is a chronological timeline; each event carries a `CatalystAssessment` from the versioned playbook (`app/config/catalyst_playbook.py`, v1.0.0) — EDITORIAL content, rendered as labeled playbook cards, never as evidence. Framing statement: beta vs SPY (measured) + per-event sensitivity "not yet measured" (event studies are a tracked follow-up). FRED® attribution shown in the workspace footer (API terms).
* **Sprint C (complete): Evidence Engine** — source registry with trust levels (`backend/app/config/evidence_sources.py`), `evidence_records` + `evidence_entities` (graph-ready, ADR-013), SEC EDGAR connector, Yahoo per-ticker news RSS connector (trust 7, defusedxml parsing), `GET /api/v1/evidence/{symbol}`, and the workspace **Company Evidence** section (filings + coverage, trust badges, links to originals, best-effort ingestion that degrades on source outages).
* **Automatic ingestion scheduler** â€” the backend process refreshes Nowflation and the Fed calendar immediately at startup and every 24 hours (configurable); jobs reuse the existing ingestion services, isolate failures, and stop cleanly.
* **Manual AI research packet (ADR-014)** — every built workspace can be copied as a versioned prompt for ChatGPT/Claude with structured statements, namespaced citations, trust levels, and source URLs. No API key or LLM call.
* **Momentum product refinement (ADR-015)** — Weekly Thesis and Intraday Execution Context are separate. M1a empirical provider verification is documented in `M1A_PROVIDER_SCORECARD.md`; no intraday provider has passed yet, so M1b was not started.
* **M2a daily momentum and relative context** — the technical read includes 9/21-day EMA distances and 1/5-day momentum. A deterministic Relative Context section compares the selected stock with SPY and QQQ (explicit ETF proxies) over 1-week/1-month/3-month windows. A What Changed section compares the current build with the immediately prior persisted workspace snapshot, including price/RSI/EMA movement and new evidence/catalysts.
* **M3 Risk Planner** — user-supplied account size, entry, invalidation, target, and dollar-risk cap produce deterministic long/short sizing, risk/reward, ATR/drawdown context, catalyst warnings, and persisted assessments. AlphaLab never chooses the invalidation and labels maximum size as a constraint, not a recommendation.
* **User-curated watchlist** — persisted symbols and notes feed a deterministic overview of daily returns, EMA distances, and SPY/QQQ-relative context. It does not rank, score, or discover securities.
* 91 backend tests (unit + integration against real TimescaleDB), ruff + mypy `--strict` clean; frontend production build clean.

**Repo:** https://github.com/sahitsharmab/alphalab — solo dev, direct commits to `main`, CI is the gate (no PRs). Commit messages must NEVER contain AI attribution lines (AGENTS.md rule).

## What Is NOT Built Yet (next work, in order)

1. **M1a provider verification:** Twelve Data Basic credentials are configured. Resume on a weekday to measure regular-session delay/current-bar finalization and investigate NBIS's 10 mismatching native-vs-derived 5m bars. Basic pre/post access is paid-only and rejected. Do not start M1b until a provider passes.
2. **M2b intraday remainder:** session structure and time-adjusted relative volume depend on M1; sector/peer context depends on sector mapping plus an explicit peer universe.
3. **Sprint B automated synthesis:** deliberately deferred while the manual packet is used.
4. **FRED/ALFRED observations** (rates, macro series with vintages — validates ADR-004): now unblocked, the key is configured.
5. **Catalyst event studies:** point-in-time per-event historical sensitivity to replace "not yet measured".
6. Deferred: ticker-scoped scheduler refresh from the new watchlist, full filing text, Treasury, and expanded market-context feeds.

## Non-Negotiable Invariants

* Layering: Connectors → Normalization → Storage → Features → Engines → Research → AI → API. Never bypass (ARCHITECTURE.md).
* All time-series storage is **bitemporal** (`observation_date`/`bar_date` + `as_of`; revisions are new rows) — ADR-004.
* Every engine output is **statements + evidence**; no prose blobs — ADR-010. Evidence links to typed entities — ADR-013.
* Trust levels measure **provenance, not truth** — ADR-011.
* Engines are deterministic; LLM calls (when they exist) go ONLY through the gateway with versioned prompts and structured outputs — ADR-006.
* Features are pure versioned functions computed on demand — ADR-008. No Redis, no auth, no event bus until a real need — ADR-007.
* Free data sources only for v0.1; run a verification **pre-task** before building any new connector (probe endpoints, check licensing) — ADR-011.
* Research is permanent: raw payloads immutable, workspace snapshots kept, nothing deleted.

## Environment (this machine — Windows 11)

* **Poetry isn't on PATH**: run `python -m poetry ...` from `backend/`.
* **Database**: `docker compose up -d db` — published on host port **5433** (a native PostgreSQL occupies 5432; do not touch it). In-compose backend uses `db:5432`.
* **Root `.env` exists locally (gitignored)** and contains `ALPHALAB_SEC_USER_AGENT` with the owner's contact email (SEC returns 403 without contact info in the UA), `ALPHALAB_FRED_API_KEY`, and `ALPHALAB_TWELVE_DATA_API_KEY`. Never commit `.env`; never hardcode secrets in the repo; never let keys reach stored URLs or logs (see the FRED connector for the pattern).
* **Frontend dev server vs container**: both want port 3000. `docker compose stop frontend` before `npm run dev`; rebuild/restart the container when done.
* Integration tests create a fresh `alphalab_test` database automatically (drop/create + alembic). They **skip** if no DB is reachable locally; CI sets `ALPHALAB_REQUIRE_DB=1` so they fail loudly there.
* `tzdata` is a required backend dependency (Windows has no system tz database).
* Beware PowerShell text-mangling of UTF-8 files (mojibake incident in Session 005) — use Python for file surgery.

## Quality Gates (run before every commit)

```bash
cd backend
python -m poetry run ruff check .        # + `ruff format .`
python -m poetry run mypy app            # strict
python -m poetry run pytest -q           # 91 tests; integration needs the compose db
cd ../frontend
npm run build                            # typecheck + build
```

CI runs the same on every push to `main` (`.github/workflows/ci.yml`). After pushing, confirm the run is green: `gh run list --repo sahitsharmab/alphalab --limit 1` (gh CLI is authenticated on this machine).

## Verification Norms (what "done" means here)

* Don't stop at unit tests: rebuild the backend container (`docker compose up --build -d backend`) and exercise the real endpoint with real provider data.
* For frontend work: verify visually. Pattern used so far: stop the compose frontend, `npm run dev`, screenshot with `playwright-core` + system Edge (`chromium.launch({channel: "msedge"})`), and actually look at the output.
* For any chart work, follow the dataviz procedure used in Sessions 004 (validated dark palette lives in `frontend/lib/theme.ts` — series colors are CVD-checked; don't invent new ones casually).

## Session Protocol (from AGENTS.md — enforced, not optional)

Start: read the five docs above; pick the highest-priority unfinished task in TASKS.md; verify dependencies.

End: update TASKS.md (check items, add discovered tasks), append a session entry to DECISIONS.md (goal/completed/challenges/debt/next task), update CHANGELOG.md if user-visible, commit, push, confirm CI green. A session is not complete until the docs are synchronized.

## Product Voice

AlphaLab teaches the user **how to think, not what to think**. No binary buy/sell outputs, ever. Evidence before opinion; every conclusion traceable to its evidence; uncertainty stated honestly. The owner is a discretionary investor who picks his own stocks — the platform's job is to make each decision better-informed.
