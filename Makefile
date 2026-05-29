.PHONY: setup dev test lint migrate db worker

setup:
	cd backend && python -m venv .venv && .venv/bin/pip install -e ".[dev]"
	cd frontend && npm install

db:
	docker compose up -d postgres

dev-backend: db
	cd backend && .venv/bin/uvicorn civicint.api.app:create_app --factory --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

worker: db
	cd backend && .venv/bin/procrastinate --app=civicint.jobs.definitions.app worker

test:
	cd backend && .venv/bin/pytest tests/ -v

lint:
	cd backend && .venv/bin/ruff check src/ tests/
	cd frontend && npm run lint

migrate:
	cd backend && .venv/bin/alembic revision --autogenerate -m "$(msg)"

upgrade:
	cd backend && .venv/bin/alembic upgrade head
