# HANDOFF.md — Continuing AlphaLab Development

Purpose: let a new engineer (human, Codex, Claude, or any AI session with no
prior context) continue this project seamlessly. Read this file first, then
the project documents in this order:

1. AGENTS.md — your role, rules, and workflow
2. PROJECT.md — vision and philosophy (note "The Evidence Engine" and the v0.1 MVP section)
3. ARCHITECTURE.md — layers and dependency rules
4. DECISIONS.md — ADR-001..013 and the session journal (read the ADRs; skim the journal)
5. TASKS.md — the backlog; the "MVP Roadmap" section is the current plan

---

## Current State (2026-07-12, Sprint C complete)

Everything below is implemented, tested, verified live, and green in CI:

* **Sprint 0** — FastAPI backend, TimescaleDB, Alembic (4 migrations), Next.js frontend, Docker Compose, GitHub Actions CI.
* **Macro slice** — Nowflation connector → bitemporal `macro_observations` → `GET /api/v1/macro/...` → dashboard with charts (`frontend/app/page.tsx`).
* **Sprint A: Investment Workspace** — Yahoo connector → bitemporal `market_bars` → pure feature functions → Technical/Historical/Inflation engines → `GET /api/v1/workspace/{symbol}` → `/workspace/[symbol]` page. Every statement carries evidence ids; the `WorkspaceSection` validator rejects untraceable claims.
* **Sprint C2 (complete): Upcoming Catalysts** — Fed calendar connector (`/json/calendar.json`, official, no key), `calendar_events` storage, Catalysts engine (next FOMC/minutes/Beige Book/stat releases; earnings dates honestly gated out — no reliable free source). CPI/jobs/GDP dates pending the owner's free FRED key (task C2-1b).
* **Sprint C (complete): Evidence Engine** — source registry with trust levels (`backend/app/config/evidence_sources.py`), `evidence_records` + `evidence_entities` (graph-ready, ADR-013), SEC EDGAR connector, Yahoo per-ticker news RSS connector (trust 7, defusedxml parsing), `GET /api/v1/evidence/{symbol}`, and the workspace **Company Evidence** section (filings + coverage, trust badges, links to originals, best-effort ingestion that degrades on source outages).
* 58 backend tests (unit + integration against real TimescaleDB), ruff + mypy `--strict` clean.

**Repo:** https://github.com/sahitsharmab/alphalab — solo dev, direct commits to `main`, CI is the gate (no PRs). Commit messages must NEVER contain AI attribution lines (AGENTS.md rule).

## What Is NOT Built Yet (next work, in order)

1. **Sprint B**: LLM Gateway (ADR-006) + workspace synthesis. **Blocked on the owner choosing the LLM provider/model and supplying an API key** (task B0).
2. **C2-1b**: CPI/jobs/GDP release dates via FRED release-dates API — **needs the owner's free FRED key** (also unblocks rates data / remaining Phase 1 macro connectors). BLS HTML was rejected (bot-blocking); per-company press-release wires are NOT free-viable (Session 007); earnings dates have no reliable free source (Session 008).
3. Scheduler for automatic ingestion (currently manual/auto-on-request).
4. Deferred: CNBC/MarketWatch general feeds (need a market-context section), full filing text retrieval, Treasury connector.

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
* **Root `.env` exists locally (gitignored)** and contains `ALPHALAB_SEC_USER_AGENT` with the owner's contact email — SEC returns 403 without contact info in the UA. Never commit `.env`; never hardcode the email in the repo.
* **Frontend dev server vs container**: both want port 3000. `docker compose stop frontend` before `npm run dev`; rebuild/restart the container when done.
* Integration tests create a fresh `alphalab_test` database automatically (drop/create + alembic). They **skip** if no DB is reachable locally; CI sets `ALPHALAB_REQUIRE_DB=1` so they fail loudly there.
* `tzdata` is a required backend dependency (Windows has no system tz database).
* Beware PowerShell text-mangling of UTF-8 files (mojibake incident in Session 005) — use Python for file surgery.

## Quality Gates (run before every commit)

```bash
cd backend
python -m poetry run ruff check .        # + `ruff format .`
python -m poetry run mypy app            # strict
python -m poetry run pytest -q           # 54 tests; integration needs the compose db
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
