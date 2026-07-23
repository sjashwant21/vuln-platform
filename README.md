# VulnAssess Platform

AI-powered vulnerability assessment platform — a production-ready, multi-tenant web application combining a FastAPI backend, a React + Vite frontend, background workers (Celery + Redis), and PostgreSQL persistence. It provides automated vulnerability analysis, report generation, and an AI-assisted intelligence layer (Groq/OpenAI integrations).

[![CI](https://img.shields.io/badge/ci-none-lightgrey)](https://github.com/sjashwant21/vuln-platform/actions)
[![License](https://img.shields.io/badge/license-ADD--LICENSE-lightgrey)](LICENSE)

Summary: FastAPI backend (async), React + Vite frontend, Celery workers, Redis, Postgres. API mounted at `/v1`, docs at `/docs`, health at `/health`.

Table of contents
- Features
- Quick start (Docker)
- Local development
- Environment variables
- Database & migrations
- Testing, linting & formatting
- Deployment notes
- Security
- Contributing
- Where to look in the code
- License & contact

## Features

- Async FastAPI backend with structured JSON logging (structlog) and robust exception handling
- React (Vite + TypeScript) frontend with Tailwind-ready config
- Background processing with Celery + Redis for long-running analysis and report generation
- PostgreSQL persistence (asyncpg) with Alembic migrations
- Report generation: DOCX, HTML and charts
- AI-assisted analysis via configurable providers (Groq primary, OpenAI fallback)
- Authentication: JWT, optional MFA, and rate limiting

## Quick start — development (Docker, recommended)

1. Copy environment template and generate secrets:

```bash
cp .env.example .env
# generate secrets (prints values, copy into .env)
make gen-secrets
```

2. Start the stack:

```bash
make up
# or
docker-compose up -d --remove-orphans
```

3. Run migrations (the API attempts an idempotent auto-migrate at startup; you can run explicitly):

```bash
make migrate
# or
docker-compose run --rm migrate
```

4. Access the services:
- Frontend: http://localhost (nginx reverse proxy)
- API docs: http://localhost/docs
- Health: http://localhost/health

Stop the stack:

```bash
make down
# or
docker-compose down
```

Notes
- The project expects secrets to be provided via `.env` for local compose runs.
- If nginx is not used locally, frontend dev server runs on the port shown by `npm run dev` (frontend).

## Step-by-Step Usage Guide

**Step 1: Access the API Documentation (Swagger UI)**
1. With the Docker stack running (`make up` or `docker compose up -d`), open your browser and go to: `http://localhost/docs` (or `http://localhost:8000/docs` if running locally).
2. This is the interactive dashboard where you can test all your endpoints without writing any frontend code.

**Step 2: Create an Organization and User (Registration)**
1. In the Swagger UI, scroll down to the **Auth** section and click on `POST /v1/auth/register`.
2. Click the **"Try it out"** button.
3. Enter test JSON data:
   ```json
   {
     "email": "admin@mycompany.com",
     "password": "Password123!",
     "full_name": "John Doe",
     "organization_name": "My Security Corp",
     "organization_slug": "my-sec-corp"
   }
   ```
4. Click **Execute**. You should get a `201 Created` response containing your new `access_token`.

**Step 3: Authenticate (Login)**
1. Scroll to the very top of the Swagger UI page and click the green **"Authorize"** button (with the padlock icon).
2. Paste the `access_token` you just received into the value box and click **Authorize**.
3. Now, every API request you make will automatically include your authentication token!

**Step 4: Test the AI Vulnerability Features (The Core Flow)**
1. **Add an Asset**: Go to the Assets endpoint (e.g., `POST /v1/assets`), click "Try it out", and add a target URL or IP address you want to scan.
2. **Trigger a Scan**: Call the scan endpoint for that asset. Because we are using Celery + Redis, this will be queued as a background task.
3. **View the AI Analysis**: Once the scan finishes, you can use the `GET /v1/scans/{scan_id}/report` endpoint. This will return the vulnerabilities found, prioritized and summarized by the AI engine!

## Local development (without Docker)

Backend (recommended Python 3.11+):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# set env vars from .env.example (DATABASE_URL, REDIS_URL, etc.)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
# To build production assets
npm run build
# Serve the preview build
npm run preview
```

To serve frontend build behind nginx (as docker-compose does), copy `dist/` into nginx/static or mount appropriately and reload nginx.

## Environment variables

See `.env.example` for a complete template. Important variables:
- APP_ENV / APP_NAME / LOG_LEVEL
- SECRET_KEY, JWT_SECRET_KEY, JWT_* settings
- DATABASE_URL (e.g. postgresql+asyncpg://user:pass@host:5432/dbname)
- REDIS_URL, CELERY_BROKER_URL, CELERY_RESULT_BACKEND
- GROQ_API_KEY and GROQ_MODEL (AI provider)
- NVD_API_KEY (optionally used for NVD lookups)

Do NOT commit real secrets.

## Database & migrations

- Alembic config and migrations live under `backend/alembic/` and `backend/alembic.ini`.
- Docker-compose provides a `migrate` service that runs `alembic upgrade head`.
- Locally (from `backend/`):

```bash
alembic -c alembic.ini upgrade head
```

If you prefer Makefile helper:
```bash
make migrate-local
```

## Tests, linting & formatting

Run backend tests and coverage:

```bash
make test
# or
cd backend && pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html
```

Unit/integration examples:
- Unit tests: `make test-unit`
- Integration tests: `make test-integration`

Lint/format and type checks:

```bash
make lint   # ruff
make fmt    # ruff format
make check  # ruff + mypy
```

## Deployment notes

- Frontend contains `frontend/vercel.json` if you want to deploy static site to Vercel.
- Backend has `railway.toml` for Railway deployments; it also supports containerized deployment via Dockerfile.
- For production, use a secrets manager (Vault/Secret Manager), enable TLS termination, and run services in an orchestrator (Kubernetes, ECS, Cloud Run, etc.).

## Background workers

- The Celery worker image is built from `backend/Dockerfile.worker`.
- Ensure `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` are configured and that Redis accepts the configured password.

## Observability & logging

- Structured JSON logs via structlog. Configure `LOG_LEVEL` in `.env`.
- docker-compose includes healthchecks for postgres, redis, api, and nginx.

## Security considerations

- Configure a strong `JWT_SECRET_KEY` and keep secrets out of VCS.
- Security headers and HSTS are applied when the app is in production mode.
- Ensure rate limiting and tenant quotas are configured for public deployments.
- TLS must be enabled in front of the app for production (nginx in this repo expects certificates to be mounted at `nginx/ssl`).

## Contributing

- Create a branch `feat/<short-desc>` or `fix/<short-desc>` off `main` and open a PR.
- Include tests for new features or bug fixes.
- Run linting & type checks: `make check`.

Maintainer: @sjashwant21

## Where to look in the code

- `backend/app/main.py` — application factory (lifespan, middleware, routers)
- `backend/pyproject.toml` & `backend/requirements.txt` — dependencies
- `backend/alembic/` — database migrations
- `frontend/src/` — frontend source
- `docker-compose.yml` and `Makefile` — dev orchestration and helpers

## License & contact

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

Contact: Shaan Jashwant (<109244010+sjashwant21@users.noreply.github.com>)
