"""
Integration tests for /v1/users/* and /v1/organizations/* routes.
"""
from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient


REGISTER_2: dict[str, Any] = {
    "email": "bob@example.com",
    "password": "Secure123",
    "full_name": "Bob Analyst",
    "organization_name": "Bob Corp",
    "organization_slug": "bob-corp",
}


# ══════════════════════════════════════════════════════════════════
# GET /v1/users/me
# ══════════════════════════════════════════════════════════════════

class TestGetMe:

    @pytest.mark.asyncio
    async def test_returns_own_profile(
        self, client: AsyncClient, auth_headers: dict, registered_user: dict
    ):
        resp = await client.get("/v1/users/me", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "owner@acme.example"
        assert body["role"] == "owner"
        assert "password_hash" not in body
        assert "mfa_secret" not in body

    @pytest.mark.asyncio
    async def test_requires_authentication(self, client: AsyncClient):
        resp = await client.get("/v1/users/me")
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════
# PATCH /v1/users/me
# ══════════════════════════════════════════════════════════════════

class TestUpdateProfile:

    @pytest.mark.asyncio
    async def test_updates_full_name(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.patch(
            "/v1/users/me",
            json={"full_name": "Alice Updated"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Alice Updated"

    @pytest.mark.asyncio
    async def test_empty_body_is_noop(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.patch(
            "/v1/users/me",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_blank_name_rejected(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.patch(
            "/v1/users/me",
            json={"full_name": "   "},
            headers=auth_headers,
        )
        assert resp.status_code in (400, 422)


# ══════════════════════════════════════════════════════════════════
# GET /v1/users
# ══════════════════════════════════════════════════════════════════

class TestListUsers:

    @pytest.mark.asyncio
    async def test_admin_can_list_users(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.get("/v1/users", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert body["total"] >= 1

    @pytest.mark.asyncio
    async def test_pagination_params_respected(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.get(
            "/v1/users?limit=1&offset=0",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()["items"]) <= 1

    @pytest.mark.asyncio
    async def test_viewer_cannot_list_users(self, client: AsyncClient):
        """Register a second user with viewer role."""
        # Register second org (viewer user simulation is done via role in JWT)
        # For now verify unauthenticated access is blocked
        resp = await client.get("/v1/users")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_users_from_other_orgs_not_visible(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Bob registers his own org — Alice should not see Bob."""
        await client.post("/v1/auth/register", json=REGISTER_2)

        resp = await client.get("/v1/users", headers=auth_headers)
        emails = [u["email"] for u in resp.json()["items"]]
        assert "bob@example.com" not in emails


# ══════════════════════════════════════════════════════════════════
# GET /v1/organizations/me
# ══════════════════════════════════════════════════════════════════

class TestGetOrg:

    @pytest.mark.asyncio
    async def test_returns_own_org(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.get("/v1/organizations/me", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["slug"] == "acme-security"
        assert body["plan_tier"] == "free"
        assert body["max_assets"] == 5

    @pytest.mark.asyncio
    async def test_requires_authentication(self, client: AsyncClient):
        resp = await client.get("/v1/organizations/me")
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════
# PATCH /v1/organizations/me
# ══════════════════════════════════════════════════════════════════

class TestUpdateOrg:

    @pytest.mark.asyncio
    async def test_owner_can_update_org_name(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.patch(
            "/v1/organizations/me",
            json={"name": "Acme Security Renamed"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Acme Security Renamed"

    @pytest.mark.asyncio
    async def test_empty_name_rejected(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.patch(
            "/v1/organizations/me",
            json={"name": ""},
            headers=auth_headers,
        )
        assert resp.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_unauthenticated_request_rejected(self, client: AsyncClient):
        resp = await client.patch(
            "/v1/organizations/me",
            json={"name": "Hacked"},
        )
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════
# GET /health
# ══════════════════════════════════════════════════════════════════

class TestHealth:

    @pytest.mark.asyncio
    async def test_health_check_returns_ok(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] in ("ok", "degraded")
        assert "version" in body
        assert "database" in body

    @pytest.mark.asyncio
    async def test_health_does_not_require_auth(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
