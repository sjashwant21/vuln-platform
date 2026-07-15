"""
Shared pytest fixtures.

Database strategy:
  - One engine per session (expensive to create)
  - One connection per test, wrapped in a SAVEPOINT
  - Rollback after every test — zero truncation cost
  - Session factory bound to that connection so service code
    uses the same transaction and the rollback covers it all

This means tests run at full transaction isolation without
needing to reset sequences or truncate tables.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings
from app.infrastructure.database.models import Base
from app.main import create_app

# ── Event loop ─────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── Database engine (session-scoped — created once) ────────────

@pytest_asyncio.fixture(scope="session")
async def db_engine():
    cfg = get_settings()
    engine = create_async_engine(
        cfg.database_url,
        echo=False,
        pool_pre_ping=True,
    )
    # Create all tables once
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after entire test session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ── Per-test DB connection with savepoint rollback ─────────────

@pytest_asyncio.fixture
async def db_connection(db_engine) -> AsyncGenerator[AsyncConnection, None]:
    """One connection per test, rolled back after."""
    async with db_engine.connect() as conn:
        await conn.begin()            # outer transaction
        await conn.begin_nested()     # SAVEPOINT — rollback target
        yield conn
        await conn.rollback()         # rolls back to SAVEPOINT


@pytest_asyncio.fixture
async def db_session(db_connection: AsyncConnection) -> AsyncGenerator[AsyncSession, None]:
    """AsyncSession bound to the per-test connection."""
    factory = async_sessionmaker(
        bind=db_connection,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with factory() as session:
        yield session


# ── Override FastAPI's get_db_session with the test session ────

@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    HTTP test client with DB dependency overridden to use the
    per-test session (so test transactions are rolled back).
    """
    from app.infrastructure.database.connection import get_db_session

    app = create_app()

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db_session] = _override_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Common data factories ───────────────────────────────────────

@pytest.fixture
def register_payload() -> dict[str, Any]:
    return {
        "email": "owner@acme.example",
        "password": "Secure123",
        "full_name": "Alice Owner",
        "organization_name": "Acme Security",
        "organization_slug": "acme-security",
    }


@pytest_asyncio.fixture
async def registered_user(
    client: AsyncClient,
    register_payload: dict[str, Any],
) -> dict[str, Any]:
    """Register + login once, return full response body."""
    resp = await client.post("/v1/auth/register", json=register_payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture
def auth_headers(registered_user: dict[str, Any]) -> dict[str, str]:
    token = registered_user["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
