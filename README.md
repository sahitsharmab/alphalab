# AlphaLab

AI-powered **Financial Intelligence Platform** — a personal quantitative research operating system.

AlphaLab is **not** a trading bot. It transforms raw financial data into structured, explainable, statistically validated research. Research comes before automation; evidence comes before opinions.

## Documentation

Read these in order before contributing:

1. [PROJECT.md](PROJECT.md) — vision and philosophy
2. [ARCHITECTURE.md](ARCHITECTURE.md) — layered architecture and rules
3. [DECISIONS.md](DECISIONS.md) — ADRs and session journal
4. [TASKS.md](TASKS.md) — development backlog (single source of truth)
5. [AGENTS.md](AGENTS.md) — AI engineer instructions

## Architecture at a Glance

```
Connectors → Normalization → Storage → Feature Store → Engines → Research → AI Analysts → Applications
```

Information flows strictly upward. No layer bypasses another. AI never talks to external APIs.

## Stack

- **Backend:** Python 3.12+, FastAPI, SQLAlchemy (async), Alembic, Pydantic v2
- **Database:** PostgreSQL + TimescaleDB
- **Frontend:** Next.js + TypeScript
- **Tooling:** Poetry, ruff, mypy (strict), pytest, Docker Compose

## Quick Start

### With Docker (recommended)

```bash
cp .env.example .env
docker compose up --build
```

- Backend: http://localhost:8000 — health at `/api/v1/health`, docs at `/docs`
- Frontend: http://localhost:3000
- Database: localhost:5433 (host port 5433 avoids clashing with native PostgreSQL installs)

### Local backend development

```bash
cd backend
poetry install
poetry run uvicorn app.main:app --reload
```

Run quality gates:

```bash
poetry run ruff check .
poetry run mypy app
poetry run pytest
```

### Local frontend development

```bash
cd frontend
npm install
npm run dev
```

## Security Posture

Single-user, localhost-first (ADR-007). No authentication is configured — do not expose this platform to the public internet as-is.

## License

Personal project. All rights reserved.
