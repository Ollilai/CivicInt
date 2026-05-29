# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

CivicInt is a Finnish municipal decision document watchdog. It scrapes municipal document platforms (CloudNC, Dynasty, TWeb), extracts text from PDFs, uses LLM triage to identify environmentally relevant decisions, and builds structured cases for advocacy professionals.

Monorepo: `backend/` (Python/FastAPI) + `frontend/` (Next.js). The old prototype in `watchdog/` is reference code only.

## Commands

### Backend
```bash
cd backend

# Setup
uv venv .venv --python 3.12
uv pip install -e ".[dev]" --python .venv/bin/python

# Tests (SQLite in-memory, no Postgres needed)
.venv/bin/python -m pytest tests/ -v
.venv/bin/python -m pytest tests/test_connectors/test_base.py::TestIsSafeUrl -v  # single class

# Lint
.venv/bin/ruff check src/ tests/ --fix

# Dev server
.venv/bin/uvicorn civicint.api.app:create_app --factory --reload --port 8000

# CLI (requires Postgres — `docker compose up -d`)
.venv/bin/civicint init-db
.venv/bin/civicint seed-lapland
.venv/bin/civicint discover
.venv/bin/civicint run-pipeline
.venv/bin/civicint stats

# Database
docker compose up -d  # Postgres 15 at localhost:5432
.venv/bin/alembic upgrade head
```

### Frontend
```bash
cd frontend
npm install
npm run dev       # localhost:3000
npx next build    # production build
```

## Architecture

### Pipeline (5 stages)
```
Source → discover → fetch → extract → triage (gpt-4o-mini) → case_builder (gpt-4o)
```

Each stage is a function in `backend/src/civicint/pipeline/` taking `(document_id, session)` or `(source_id, session)`.

**Document status flow**: `NEW → FETCHED → EXTRACTED → TRIAGED → BUILT` (or `ERROR` / `BUDGET_PAUSED`).

### Connector Registry
Platform name → connector class via `CONNECTOR_REGISTRY` in `connectors/__init__.py`:
- **CloudNC** — Enontekiö, Muonio, Rovaniemi (RSS → HTML fallback)
- **Dynasty** — Inari, Kemi, Kemijärvi, Kittilä, etc. (multiple RSS paths → HTML)
- **TWeb** — Keminmaa, Kolari, Pello, Sodankylä, etc. (table parsing)

Adding a municipality is configuration (seed data in `cli.py`), not code.

### Security
- SSRF protection: `is_safe_url()` blocks private IP ranges before DNS resolution
- Path traversal: `safe_path_join()` in extract stage
- LLM budget: monthly cost cap via `llm_usage` table, `BUDGET_PAUSED` status

### Data Model
Core: `Source → Document → File/FileText → Case → Evidence + CaseEvent`
Supporting: `Organization, User, WatchProfile, Bookmark, LLMUsage`

### Frontend
Next.js 15+ App Router with:
- `/` — case feed with filters
- `/cases/[slug]` — case detail with evidence + timeline
- `/municipalities` — municipality grid
- `/admin` — pipeline stats + LLM spend
- Auth.js v5 (optional email magic link)

## Conventions

- Ruff: line-length 100, target py311, rules E/F/I/W/UP/B
- Tests use SQLite in-memory (JSONB→JSON shim in conftest.py)
- Pipeline functions take a SQLAlchemy `Session` parameter
- LLM output is Finnish; triage prompts are English
- Frontend text is Finnish; code/variable names are English

## Environment Variables

Backend: `DATABASE_URL`, `OPENAI_API_KEY`, `SECRET_KEY`, `LLM_MONTHLY_BUDGET` (see `backend/.env.example`)
Frontend: `NEXT_PUBLIC_API_URL`, `NEXTAUTH_SECRET` (see `frontend/.env.local.example`)
