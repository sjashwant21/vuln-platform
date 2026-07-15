"""
Integration tests for /v1/auth/* routes.

These use the real FastAPI app with a real (test) PostgreSQL database.
Every test runs inside a transaction that is rolled back after the test,
so tests are isolated and leave no state.
"""
from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient


# ── Fixtures ───────────────────────────────────────────────────

REGISTER_PAYLOAD: dict[str, Any] = {
    "email": "alice@example.com",
    "password": "Secure123",
    "full_name": "Alice Owner",
    "organization_name": "Acme Corp",
    "organization_slug": "acme-corp",
}


# ══════════════════════════════════════════════════════════════════
# POST /v1/auth/register
# ══════════════════════════════════════════════════════════════════

class TestRegister:

    @pytest.mark.asyncio
    async def test_successful_registration(self, client: AsyncClient):
        resp = await client.post("/v1/auth/register", json=REGISTER_PAYLOAD)

        assert resp.status_code == 201
        body = resp.json()
        assert body["user"]["email"] == "alice@example.com"
        assert body["user"]["role"] == "owner"
        assert body["organization"]["slug"] == "acme-corp"
        assert body["organization"]["plan_tier"] == "free"
        assert "access_token" in body["tokens"]
        assert "refresh_token" in body["tokens"]

    @pytest.mark.asyncio
    async def test_tokens_are_non_empty_strings(self, client: AsyncClient):
        resp = await client.post("/v1/auth/register", json=REGISTER_PAYLOAD)
        body = resp.json()
        assert len(body["tokens"]["access_token"]) > 20
        assert len(body["tokens"]["refresh_token"]) > 20

    @pytest.mark.asyncio
    async def test_duplicate_email_returns_409(self, client: AsyncClient):
        await client.post("/v1/auth/register", json=REGISTER_PAYLOAD)
        resp = await client.post("/v1/auth/register", json=REGISTER_PAYLOAD)

        assert resp.status_code == 409
        assert "email" in resp.json()["error"].lower()

    @pytest.mark.asyncio
    async def test_duplicate_slug_returns_409(self, client: AsyncClient):
        await client.post("/v1/auth/register", json=REGISTER_PAYLOAD)
        different_email = {**REGISTER_PAYLOAD, "email": "bob@example.com"}
        resp = await client.post("/v1/auth/register", json=different_email)

        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_weak_password_returns_422(self, client: AsyncClient):
        payload = {**REGISTER_PAYLOAD, "password": "weak"}
        resp = await client.post("/v1/auth/register", json=payload)
        assert resp.status_code in (422, 400)

    @pytest.mark.asyncio
    async def test_invalid_email_returns_422(self, client: AsyncClient):
        payload = {**REGISTER_PAYLOAD, "email": "not-an-email"}
        resp = await client.post("/v1/auth/register", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_slug_returns_422(self, client: AsyncClient):
        payload = {**REGISTER_PAYLOAD, "organization_slug": "INVALID SLUG!"}
        resp = await client.post("/v1/auth/register", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_required_fields_returns_422(self, client: AsyncClient):
        resp = await client.post("/v1/auth/register", json={"email": "x@x.com"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_response_has_request_id_header(self, client: AsyncClient):
        resp = await client.post("/v1/auth/register", json=REGISTER_PAYLOAD)
        assert "x-request-id" in resp.headers

    @pytest.mark.asyncio
    async def test_password_not_in_response(self, client: AsyncClient):
        resp = await client.post("/v1/auth/register", json=REGISTER_PAYLOAD)
        body_str = resp.text
        assert "Secure123" not in body_str
        assert "password_hash" not in body_str


# ══════════════════════════════════════════════════════════════════
# POST /v1/auth/login
# ══════════════════════════════════════════════════════════════════

class TestLogin:

    @pytest.mark.asyncio
    async def test_valid_credentials_return_tokens(
        self, client: AsyncClient, registered_user: dict
    ):
        resp = await client.post(
            "/v1/auth/login",
            json={"email": "owner@acme.example", "password": "Secure123"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["token_type"] == "bearer"
        assert body["expires_in"] == 900

    @pytest.mark.asyncio
    async def test_wrong_password_returns_401(
        self, client: AsyncClient, registered_user: dict
    ):
        resp = await client.post(
            "/v1/auth/login",
            json={"email": "owner@acme.example", "password": "WrongPass1"},
        )
        assert resp.status_code == 401
        assert "www-authenticate" in resp.headers

    @pytest.mark.asyncio
    async def test_unknown_email_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/v1/auth/login",
            json={"email": "ghost@example.com", "password": "Secure123"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_password_returns_422(self, client: AsyncClient):
        resp = await client.post(
            "/v1/auth/login",
            json={"email": "owner@acme.example", "password": ""},
        )
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════
# POST /v1/auth/refresh
# ══════════════════════════════════════════════════════════════════

class TestRefresh:

    @pytest.mark.asyncio
    async def test_valid_refresh_token_returns_new_pair(
        self, client: AsyncClient, registered_user: dict
    ):
        old_refresh = registered_user["tokens"]["refresh_token"]
        old_access  = registered_user["tokens"]["access_token"]

        resp = await client.post(
            "/v1/auth/refresh",
            json={"refresh_token": old_refresh},
        )
        assert resp.status_code == 200
        body = resp.json()
        # New tokens issued
        assert body["access_token"] != old_access
        assert body["refresh_token"] != old_refresh

    @pytest.mark.asyncio
    async def test_used_refresh_token_returns_401(
        self, client: AsyncClient, registered_user: dict
    ):
        """Token rotation — once used, the old token is invalid."""
        old_refresh = registered_user["tokens"]["refresh_token"]

        # Use it once
        await client.post("/v1/auth/refresh", json={"refresh_token": old_refresh})
        # Try to reuse
        resp = await client.post("/v1/auth/refresh", json={"refresh_token": old_refresh})

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_bogus_refresh_token_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/v1/auth/refresh",
            json={"refresh_token": "this-is-not-a-real-token"},
        )
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════
# POST /v1/auth/logout
# ══════════════════════════════════════════════════════════════════

class TestLogout:

    @pytest.mark.asyncio
    async def test_logout_invalidates_refresh_token(
        self, client: AsyncClient, registered_user: dict, auth_headers: dict
    ):
        refresh = registered_user["tokens"]["refresh_token"]

        resp = await client.post(
            "/v1/auth/logout",
            json={"refresh_token": refresh},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "logged out" in resp.json()["message"].lower()

        # Refresh should now fail
        resp2 = await client.post(
            "/v1/auth/refresh",
            json={"refresh_token": refresh},
        )
        assert resp2.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/v1/auth/logout",
            json={"refresh_token": "any-token"},
        )
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════
# GET /v1/auth/me
# ══════════════════════════════════════════════════════════════════

class TestMe:

    @pytest.mark.asyncio
    async def test_me_returns_user_identity(
        self, client: AsyncClient, auth_headers: dict, registered_user: dict
    ):
        resp = await client.get("/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "owner@acme.example"
        assert body["role"] == "owner"

    @pytest.mark.asyncio
    async def test_me_without_token_returns_401(self, client: AsyncClient):
        resp = await client.get("/v1/auth/me")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_me_with_malformed_token_returns_401(self, client: AsyncClient):
        resp = await client.get(
            "/v1/auth/me",
            headers={"Authorization": "Bearer not.a.jwt"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_me_with_expired_token_returns_401(self, client: AsyncClient):
        """Generate a token that is already expired."""
        from datetime import timedelta
        from jose import jwt
        from app.config import get_settings
        import time

        cfg = get_settings()
        payload = {
            "sub": "user-1",
            "org": "org-1",
            "role": "owner",
            "email": "x@x.com",
            "type": "access",
            "exp": int(time.time()) - 1,  # already expired
        }
        token = jwt.encode(payload, cfg.jwt_secret_key, algorithm=cfg.jwt_algorithm)

        resp = await client.get(
            "/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════
# POST /v1/auth/change-password
# ══════════════════════════════════════════════════════════════════

class TestChangePassword:

    @pytest.mark.asyncio
    async def test_valid_change_returns_200(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            "/v1/auth/change-password",
            json={"current_password": "Secure123", "new_password": "NewSecure9"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "password changed" in resp.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_wrong_current_password_returns_401(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            "/v1/auth/change-password",
            json={"current_password": "WrongOld1", "new_password": "NewSecure9"},
            headers=auth_headers,
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_weak_new_password_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            "/v1/auth/change-password",
            json={"current_password": "Secure123", "new_password": "weak"},
            headers=auth_headers,
        )
        assert resp.status_code in (422, 400)

    @pytest.mark.asyncio
    async def test_change_password_revokes_existing_session(
        self, client: AsyncClient, registered_user: dict, auth_headers: dict
    ):
        """After password change all refresh tokens are revoked."""
        old_refresh = registered_user["tokens"]["refresh_token"]

        await client.post(
            "/v1/auth/change-password",
            json={"current_password": "Secure123", "new_password": "NewSecure9"},
            headers=auth_headers,
        )

        resp = await client.post(
            "/v1/auth/refresh",
            json={"refresh_token": old_refresh},
        )
        assert resp.status_code == 401
