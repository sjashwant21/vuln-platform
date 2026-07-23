"""
Async database engine and session management.

Architecture decisions:
  - Engine is a module-level singleton — created once, shared across workers
  - AsyncSession per request via FastAPI DI — never share sessions across requests
  - expire_on_commit=False — prevents post-commit lazy-load AttributeErrors
  - pool_pre_ping=True — detects stale connections before use (essential in containers)
  - pool_recycle=3600 — avoids hitting PostgreSQL's idle connection timeout
"""
from __future__ import annotations

import structlog
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings, get_settings

logger = structlog.get_logger(__name__)

# Module-level singletons — initialised by create_engine_and_factory()
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_engine_and_factory(settings: Settings | None = None) -> None:
    """
    Initialise the engine and session factory.
    Called once from the FastAPI lifespan startup hook.
    """
    global _engine, _session_factory

    cfg = settings or get_settings()

    # Build the async URL
    db_url = cfg.database_url

    # asyncpg doesn't understand sslmode= query param — strip it and use connect_args instead
    ssl_required = "sslmode=require" in db_url or "sslmode=verify-full" in db_url
    if "sslmode=" in db_url:
        import re
        db_url = re.sub(r"[?&]sslmode=[^&]*", "", db_url).rstrip("?&")

    # Set SSL connect_args for asyncpg (needs ssl=True, not a string)
    connect_args: dict = {}
    if ssl_required:
        connect_args = {"ssl": True}

    _engine = create_async_engine(
        db_url,
        pool_size=cfg.database_pool_size,
        max_overflow=cfg.database_max_overflow,
        pool_timeout=cfg.database_pool_timeout,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=cfg.is_development,   # SQL logging in dev only — never in prod
        connect_args=connect_args,
    )

    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,   # Avoids lazy-load errors after commit
        autocommit=False,
        autoflush=False,
    )

    logger.info(
        "database_engine_created",
        pool_size=cfg.database_pool_size,
        max_overflow=cfg.database_max_overflow,
    )


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError(
            "Database engine not initialised. "
            "Ensure create_engine_and_factory() is called in the lifespan hook."
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError(
            "Session factory not initialised. "
            "Ensure create_engine_and_factory() is called in the lifespan hook."
        )
    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — yields a scoped async session.

    Transaction lifecycle:
      - Begin: implicit on first statement
      - Commit: on successful response
      - Rollback: on any exception (including HTTP exceptions raised by routes)
      - Close: always, even if rollback raised

    Usage:
        @router.get("/")
        async def endpoint(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_engine() -> None:
    """
    Dispose the engine and release all pooled connections.
    Called from the FastAPI lifespan shutdown hook.
    """
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        logger.info("database_engine_disposed")
        _engine = None
        _session_factory = None
