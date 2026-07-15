"""
FastAPI application factory.

Responsibilities:
  1. Lifespan — initialise DB engine on startup, dispose on shutdown
  2. Middleware — request ID, CORS, security headers
  3. Exception handlers — map domain exceptions → HTTP responses
  4. Router registration — versioned API prefix
  5. OpenAPI metadata — title, version, security scheme
"""
from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.middleware.request_context import RequestContextMiddleware
from app.api.v1 import auth, health, organizations, users, analysis, intelligence, reports
from app.config import get_settings
from app.domain.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ExternalServiceError,
    PlanLimitError,
    ResourceConflictError,
    ResourceNotFoundError,
    ValidationError,
    VulnAssessError,
)
from app.infrastructure.database.connection import (
    close_engine,
    create_engine_and_factory,
)

logger = structlog.get_logger(__name__)


# ── Logging setup ──────────────────────────────────────────────

def _configure_logging(log_level: str) -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper(), logging.INFO),
    )


# ── Lifespan ───────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Startup: initialise DB connection pool.
    Shutdown: dispose pool (returns connections to PostgreSQL).
    """
    cfg = get_settings()
    _configure_logging(cfg.log_level)

    logger.info("application_starting", env=cfg.app_env, version=cfg.app_version)
    create_engine_and_factory(cfg)

    yield  # ← application runs here

    logger.info("application_shutting_down")
    await close_engine()


# ── Application factory ────────────────────────────────────────

def create_app() -> FastAPI:
    cfg = get_settings()

    app = FastAPI(
        title="VulnAssess Platform API",
        version=cfg.app_version,
        description=(
            "AI-Powered Vulnerability Assessment Platform. "
            "Multi-tenant, async, production-grade."
        ),
        docs_url="/docs" if not cfg.is_production else None,
        redoc_url="/redoc" if not cfg.is_production else None,
        openapi_url="/openapi.json" if not cfg.is_production else None,
        lifespan=lifespan,
    )

    # ── Middleware (applied in reverse order — last added = outermost) ──

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestContextMiddleware)

    # ── Security headers ────────────────────────────────────────
    @app.middleware("http")
    async def security_headers(request: Request, call_next: object) -> JSONResponse:
        import inspect
        if inspect.iscoroutinefunction(call_next):
            response = await call_next(request)  # type: ignore[arg-type]
        else:
            response = await call_next(request)  # type: ignore[arg-type, misc]
        response.headers["X-Content-Type-Options"]    = "nosniff"
        response.headers["X-Frame-Options"]           = "DENY"
        response.headers["X-XSS-Protection"]          = "1; mode=block"
        response.headers["Referrer-Policy"]           = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"]        = "geolocation=(), microphone=()"
        if cfg.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response  # type: ignore[return-value]

    # ── Exception handlers ─────────────────────────────────────

    @app.exception_handler(AuthenticationError)
    async def handle_auth_error(request: Request, exc: AuthenticationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": exc.message, "detail": exc.detail},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(AuthorizationError)
    async def handle_authz_error(request: Request, exc: AuthorizationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": exc.message, "detail": exc.detail},
        )

    @app.exception_handler(ResourceNotFoundError)
    async def handle_not_found(request: Request, exc: ResourceNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": exc.message, "detail": exc.detail},
        )

    @app.exception_handler(ResourceConflictError)
    async def handle_conflict(request: Request, exc: ResourceConflictError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": exc.message, "detail": exc.detail},
        )

    @app.exception_handler(ValidationError)
    async def handle_validation(request: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": exc.message, "detail": exc.detail},
        )

    @app.exception_handler(PlanLimitError)
    async def handle_plan_limit(request: Request, exc: PlanLimitError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            content={"error": exc.message, "detail": exc.detail},
        )

    @app.exception_handler(ExternalServiceError)
    async def handle_external(request: Request, exc: ExternalServiceError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"error": exc.message, "detail": exc.detail},
        )

    @app.exception_handler(VulnAssessError)
    async def handle_base_error(request: Request, exc: VulnAssessError) -> JSONResponse:
        logger.error("unhandled_domain_error", error=exc.message, exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal server error", "detail": exc.detail},
        )

    # ── Routers ────────────────────────────────────────────────

    API_PREFIX = "/v1"

    app.include_router(health.router)                                    # /health
    app.include_router(auth.router,          prefix=API_PREFIX)          # /v1/auth/*
    app.include_router(users.router,         prefix=API_PREFIX)          # /v1/users/*
    app.include_router(organizations.router, prefix=API_PREFIX)          # /v1/organizations/*
    app.include_router(analysis.router,      prefix=API_PREFIX)          # /v1/analysis/*
    app.include_router(intelligence.router,  prefix=API_PREFIX)          # /v1/intelligence/*
    app.include_router(reports.router,       prefix=API_PREFIX)          # /v1/reports/*

    logger.info("application_ready", prefix=API_PREFIX)
    return app


# Module-level app instance consumed by uvicorn
app = create_app()
