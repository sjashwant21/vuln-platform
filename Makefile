# ── VulnAssess Platform — Developer Makefile ───────────────────
.PHONY: help up down build migrate shell test lint fmt check

help:
	@echo ""
	@echo "  make up        Start all services (docker compose up -d)"
	@echo "  make down      Stop all services"
	@echo "  make build     Rebuild images"
	@echo "  make migrate   Run Alembic migrations"
	@echo "  make shell     Open a shell in the api container"
	@echo "  make test      Run the full test suite"
	@echo "  make lint      Run ruff linter"
	@echo "  make fmt       Auto-format with ruff"
	@echo "  make check     lint + type-check (mypy)"
	@echo ""

# ── Docker ─────────────────────────────────────────────────────
up:
	docker compose up -d --remove-orphans

down:
	docker compose down

build:
	docker compose build --no-cache

logs:
	docker compose logs -f api worker

# ── Database ───────────────────────────────────────────────────
migrate:
	docker compose run --rm migrate

migrate-local:
	cd backend && DATABASE_URL=$$(grep DATABASE_URL ../.env | cut -d= -f2) \
	    alembic upgrade head

new-migration:
	cd backend && alembic revision --autogenerate -m "$(MSG)"

# ── Shell ──────────────────────────────────────────────────────
shell:
	docker compose exec api /bin/bash

shell-db:
	docker compose exec postgres psql -U vulnassess_user vulnassess

# ── Tests ──────────────────────────────────────────────────────
test:
	cd backend && pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html

test-unit:
	cd backend && pytest tests/unit/ -v

test-integration:
	cd backend && pytest tests/integration/ -v

test-fast:
	cd backend && pytest tests/unit/ -v -x --tb=short

# ── Code quality ───────────────────────────────────────────────
lint:
	cd backend && ruff check app/ tests/

fmt:
	cd backend && ruff format app/ tests/

check: lint
	cd backend && mypy app/ --ignore-missing-imports

# ── Secrets helper ─────────────────────────────────────────────
gen-secrets:
	@echo "SECRET_KEY=$$(openssl rand -hex 32)"
	@echo "JWT_SECRET_KEY=$$(openssl rand -hex 64)"
	@echo "POSTGRES_PASSWORD=$$(openssl rand -base64 24 | tr -d '=+/')"
	@echo "REDIS_PASSWORD=$$(openssl rand -base64 24 | tr -d '=+/')"
