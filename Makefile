.PHONY: help install dev down test test-backend test-frontend e2e lint typecheck migrate evals build

help:
	@echo "Velvic Monitor — make targets"
	@echo "  install        install backend + frontend deps"
	@echo "  dev            run backend + frontend + worker locally (compose)"
	@echo "  down           stop the local stack"
	@echo "  test           run all unit + property + integration tests"
	@echo "  test-backend   pytest"
	@echo "  test-frontend  vitest"
	@echo "  e2e            playwright"
	@echo "  lint           ruff + black --check + mypy + eslint + tsc"
	@echo "  typecheck      mypy + tsc only"
	@echo "  migrate        alembic upgrade head"
	@echo "  evals          promptfoo eval"
	@echo "  build          production build of frontend"

install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

dev:
	docker compose up --build

down:
	docker compose down -v

test: test-backend test-frontend

test-backend:
	cd backend && pytest

test-frontend:
	cd frontend && npm test

e2e:
	cd frontend && npx playwright install --with-deps chromium && npm run e2e

lint:
	cd backend && ruff check . && black --check . && mypy app
	cd frontend && npm run lint && npm run typecheck

typecheck:
	cd backend && mypy app
	cd frontend && npm run typecheck

migrate:
	cd backend && alembic upgrade head

evals:
	cd evals && npx promptfoo eval -c promptfoo.yaml

build:
	cd frontend && npm run build
