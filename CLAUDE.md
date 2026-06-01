# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

CivicInt is a Finnish municipal decision document watchdog. It scrapes municipal document platforms (CloudNC, Dynasty, TWeb), extracts text from PDFs, uses LLM triage to identify environmentally relevant decisions, and builds structured cases for advocacy professionals.

Monorepo: `backend/` (Python/FastAPI) + `frontend/` (Next.js). The old prototype in `watchdog/` is reference code only.

## Commands

### Backend (from `backend/`)
```bash
# Setup
uv venv .venv --python 3.12
uv pip install -e ".[dev]" --python .venv/bin/python

# Tests (SQLite in-memory, no Postgres needed)
.venv/bin/python -m pytest tests/ -v
.venv/bin/python -m pytest tests/test_connectors/test_base.py::TestIsSafeUrl -v  # single class

# Lint
.venv/bin/ruff check src/ tests/ --fix

# Dev server (needs Postgres)
.venv/bin/uvicorn civicint.api.app:create_app --factory --reload --port 8000

# CLI (needs Postgres — `docker compose up -d` from repo root)
.venv/bin/civicint init-db
.venv/bin/civicint seed-lapland
.venv/bin/civicint discover
.venv/bin/civicint run-pipeline
.venv/bin/civicint stats

# Migrations
.venv/bin/alembic upgrade head
.venv/bin/alembic revision --autogenerate -m "description"
```

### Frontend (from `frontend/`)
```bash
npm install
npm run dev       # localhost:3000
npx next build    # production build
npm run lint
```

### Root Makefile shortcuts
```bash
make setup          # backend venv + frontend npm install
make db             # docker compose up -d postgres
make dev-backend    # uvicorn with reload (starts postgres first)
make dev-frontend   # npm run dev
make test           # pytest
make lint           # ruff + eslint
make upgrade        # alembic upgrade head
make migrate msg="description"  # alembic autogenerate
```

### Database
```bash
docker compose up -d  # Postgres 15 at localhost:5433 (civicint:civicint)
```

## Architecture

### Pipeline (5 stages)
```
Source → discover → fetch → extract → triage (gpt-4o-mini) → case_builder (gpt-4o)
```

Each stage is a function in `backend/src/civicint/pipeline/` taking `(document_id, session)` or `(source_id, session)`. Stages are idempotent — each checks document status before processing.

**Document status flow**: `NEW → FETCHED → EXTRACTED → TRIAGED → BUILT` (or `ERROR` / `BUDGET_PAUSED`).

**Stage details**:
- **discover**: Connector.discover() → creates Document + File records, deduplicates by `(source_id, external_id)`
- **fetch**: Downloads PDFs via httpx, stores to disk, computes SHA-256
- **extract**: pdfplumber for text; OCR fallback (Tesseract) if <100 chars from file >10KB
- **triage**: GPT-4o-mini classifies environmental relevance (truncated to 12k chars). Records LLMUsage
- **case_builder**: GPT-4o synthesizes cases (truncated to 24k chars). Only runs if triage_score >= 0.6. Deduplicates cases by permit_number. Records LLMUsage

### Connector Registry
Platform name → connector class via `CONNECTOR_REGISTRY` in `connectors/__init__.py`:
- **CloudNC** — Enontekiö, Muonio, Rovaniemi (RSS → HTML fallback)
- **Dynasty** — Inari, Kemi, Kemijärvi, Kittilä, etc. (multiple RSS paths → HTML)
- **TWeb** — Keminmaa, Kolari, Pello, Sodankylä, etc. (table parsing)

All connectors inherit `BaseConnector` which provides httpx client, retry with exponential backoff (429/503), and per-domain rate limiting. Adding a municipality is configuration (seed data in `cli.py`), not code.

### Security
- SSRF protection: `is_safe_url()` in `connectors/base.py` blocks private IP ranges before DNS resolution
- Path traversal: `safe_path_join()` in extract stage
- LLM budget: monthly cost cap via `llm_usage` table, `BUDGET_PAUSED` status

### Data Model
Core: `Source → Document → File/FileText → Case → Evidence + CaseEvent`
Supporting: `Organization, User, WatchProfile, Bookmark, LLMUsage`

Key enums in `models/enums.py`: `DocumentStatus`, `TextStatus`, `CaseStatus`, `Confidence`, `UserRole`.

### API
FastAPI factory pattern (`create_app()`) with routers:
- `/api/v1/cases` — paginated list with filters, detail by slug, bookmarks
- `/api/v1/municipalities` — aggregate case counts
- `/api/v1/admin` — pipeline stats, LLM spend, source status
- `/health` — ping

Pydantic response schemas in `api/schemas/` match frontend TypeScript types manually.

### Frontend
Next.js 15+ App Router with React 19, Tailwind CSS 4, Auth.js v5 (optional magic link):
- `/` — case feed with FilterBar (municipality, category, status, confidence, search)
- `/cases/[slug]` — case detail with evidence + timeline
- `/municipalities` — municipality grid
- `/admin` — pipeline stats + LLM spend

API client in `lib/api.ts` fetches from `NEXT_PUBLIC_API_URL` (default `http://localhost:8000/api/v1`). Types in `lib/types.ts`.

**Important**: Next.js 16 has breaking changes from training data. Read `node_modules/next/dist/docs/` before writing frontend code.

## Conventions

- Ruff: line-length 100, target py311, rules E/F/I/W/UP/B
- Ruff ignores: F821 (SQLAlchemy forward-ref strings), B008 (FastAPI Depends defaults), UP042 (str+enum for Postgres)
- Tests use SQLite in-memory (JSONB→JSON shim in conftest.py)
- Pipeline functions take a SQLAlchemy `Session` parameter; caller manages commit/rollback
- Connectors are async (httpx); pipeline stages are sync (SQLAlchemy sessions)
- LLM output is Finnish; triage prompts are English
- Frontend text is Finnish; code/variable names are English

## Environment Variables

Backend: `DATABASE_URL` (must use `postgresql+psycopg://` driver prefix), `OPENAI_API_KEY`, `SECRET_KEY`, `LLM_MONTHLY_BUDGET`, `STORAGE_PATH` (see `backend/.env.example`)
Frontend: `NEXT_PUBLIC_API_URL`, `NEXTAUTH_SECRET` (see `frontend/.env.local.example`)
