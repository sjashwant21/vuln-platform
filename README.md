# VulnAssess Platform

AI-powered vulnerability assessment platform — a production-ready, multi-tenant web application combining a FastAPI backend, a React + Vite frontend, background workers (Celery + Redis), and PostgreSQL persistence. It provides automated vulnerability analysis, report generation, and an AI-assisted intelligence layer (Groq/OpenAI integrations).

- Status: Work-in-progress
- API prefix: /v1
- Docs: /docs (FastAPI interactive docs)
- Health: /health
- OpenAPI: /openapi.json

## Features

- Async FastAPI backend with structured logging and robust error handling
- React (Vite + TypeScript) frontend with Tailwind-based styling
- Background processing using Celery + Redis
- PostgreSQL persistence with Alembic migrations
- Report generation (DOCX / HTML / charts)
- AI-assisted analysis via Groq (configurable) and OpenAI fallback
- Rate-limiting, JWT auth, MFA support, and policy/plan limits

## Tech stack

- Language(s): Python (backend), TypeScript + React (frontend)
- Backend: FastAPI, Uvicorn, SQLAlchemy (async), Alembic
- Worker/Queue: Celery + Redis
- Database: PostgreSQL (asyncpg)
- Frontend: React + Vite + TypeScript
- Notable libs: pydantic, structlog, httpx, python-docx, Jinja2, recharts, @tanstack/react-query

## Repository structure (top-level)

```
.env.example            # example environment variables
Makefile                # developer convenience tasks (up, build, migrate, test, lint...)
docker-compose.yml      # docker-compose orchestration for full stack
nginx/                  # nginx config and TLS helpers
backend/                # FastAPI backend (app/, Dockerfile, alembic, tests, pyproject)
frontend/               # React + Vite frontend (src/, package.json, vite.config.ts)
```

How it fits together:
- nginx sits in front, proxying to the FastAPI API and serving the frontend build.
- The API (backend) exposes /v1/* endpoints and provides health and docs routes.
- Celery worker picks up long-running analysis/report jobs via Redis.
- PostgreSQL stores tenants, users, reports and analysis results; Alembic manages schema migrations.

## Quick start — development (Docker, recommended)

1. Copy .env example and fill required secrets:
   - cp .env.example .env
   - Use `make gen-secrets` to generate secure values for SECRET_KEY, JWT_SECRET_KEY, POSTGRES_PASSWORD, REDIS_PASSWORD

2. Bring up the full stack:
```
# from repo root
make up
# or
docker-compose up -d --remove-orphans
```

3. Run migrations (the app attempts auto-migrate on startup, but you can run explicitly):
```
make migrate
# or (runs alembic inside docker)
docker-compose run --rm migrate
```

4. View:
- Frontend: http://localhost (nginx serves the frontend build on 80)
- API docs: http://localhost/docs
- Health: http://localhost/health

Stop the stack:
```
make down
# or
docker-compose down
```

## Quick start — local development without Docker

Backend:
```
# from repo root
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# set DATABASE_URL and REDIS_URL (see .env.example)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:
```
cd frontend
npm install
npm run dev
# preview production build
npm run build
npm run preview
```

Notes:
- When running backend locally, set env vars from `.env.example` or a virtual environment.
- The backend module exposes `app` in `backend/app/main.py` and uses Alembic for migrations.

## Environment variables

A full template is in `.env.example`. Important ones include:
- APP_ENV / APP_NAME / LOG_LEVEL
- SECRET_KEY, JWT_SECRET_KEY, JWT_* settings
- DATABASE_URL (postgresql+asyncpg://...)
- REDIS_URL, CELERY_BROKER_URL, CELERY_RESULT_BACKEND
- GROQ_API_KEY, GROQ_MODEL (AI provider settings)
- NVD_API_KEY (for NVD vulnerability lookups)

Always keep real secrets out of source control.

## Database & migrations

- Alembic config lives under `backend/` (alembic.ini and migrations).
- Docker path: the `migrate` service in docker-compose runs Alembic to upgrade head.
- Local: from `backend/` you can run `alembic upgrade head` (the Makefile includes a convenience `migrate-local` target).

## Tests, linting & formatting

- Run test suite (backend):
```
make test
# or
cd backend && pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html
```

- Unit / integration split:
  - Unit: `make test-unit`
  - Integration: `make test-integration`

- Lint & format:
```
make lint    # ruff
make fmt     # ruff format
make check   # lint + mypy
```

## CI / Deployment notes

- Frontend is configured for Vercel (see `frontend/vercel.json`).
- Backend contains `railway.toml` and can be deployed to platforms supporting Docker/containers.
- docker-compose provides a reproducible environment for testing and demo deployments; for production, replace compose with orchestration (K8s/Cloud Run) and properly manage secrets & TLS.

## Background workers

- The `worker` service builds from `backend/Dockerfile.worker` and runs Celery workers using Redis as broker/result backend.
- Ensure `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` are set and Redis is reachable.

## Observability & logging

- Structured JSON logging via structlog.
- Healthchecks are configured for postgres, redis, api, and nginx in docker-compose.

## Security considerations

- JWT-based auth (configure strong `JWT_SECRET_KEY`).
- Bcrypt rounds, rate-limiting, and security headers are included.
- Always run behind TLS (nginx folder contains example nginx conf and SSL mounting).
- Do not commit production `.env` files or secrets.

## Contributing

- Please open issues for features or bugs.
- Follow the code style: Python formatting via `ruff`, typing via `mypy`.
- Create feature branches and open PRs with tests for new behavior.

Suggested branch workflow:
- branch: feat/<short-desc>
- PR target: main
- Include test coverage for new features.

## Roadmap / TODO (examples)

- Add end-to-end tests (frontend + backend CI)
- Add role-based access control & audit logs
- Add rate-limiting per tenant & quota dashboards
- Integrate additional AI providers and model selector

## License

Add a LICENSE file to declare the project license (e.g., MIT). This repository currently has no LICENSE file — choose and add one before publishing.

## Where to look in the code

- backend/app/main.py — application factory, routers, exception handlers, lifespan and startup behavior
- backend/pyproject.toml & backend/requirements.txt — backend dependencies and test/dev extras
- backend/alembic/ — migrations
- frontend/package.json & frontend/src/ — frontend app and build scripts
- docker-compose.yml — how services are wired for local/dev deployments
- Makefile — common developer commands (up/down/build/migrate/test/lint)

---

If you'd like, I can:
- Create this README.md file in the repo (draft a commit) or
- Produce shorter or longer variants (one-page overview, or an expanded developer handbook with architecture diagrams and examples).
