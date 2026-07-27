import pytest
from httpx import AsyncClient

from app.domain.enums import ScanStatus


@pytest.mark.asyncio
async def test_create_scan_job(
    client: AsyncClient,
    registered_user: dict,
):
    """Test creating a new scan job."""

    auth_headers = {"Authorization": f"Bearer {registered_user['access_token']}"}

    payload = {
        "target_ips": ["127.0.0.1", "192.168.1.1"],
        "scan_type": "discovery",
        "scan_options": {"aggressiveness": "high"}
    }

    resp = await client.post("/v1/scans", json=payload, headers=auth_headers)
    assert resp.status_code == 201

    data = resp.json()
    assert data["status"] == ScanStatus.PENDING.value
    assert data["target_ips"] == ["127.0.0.1", "192.168.1.1"]
    assert "id" in data


@pytest.mark.asyncio
async def test_list_scan_jobs(
    client: AsyncClient,
    registered_user: dict,
):
    """Test listing scan jobs."""
    auth_headers = {"Authorization": f"Bearer {registered_user['access_token']}"}

    # Create one first
    payload = {"target_ips": ["10.0.0.1"], "scan_type": "quick"}
    await client.post("/v1/scans", json=payload, headers=auth_headers)

    # List
    resp = await client.get("/v1/scans", headers=auth_headers)
    assert resp.status_code == 200

    data = resp.json()
    assert len(data) >= 1
    assert data[0]["target_ips"] == ["10.0.0.1"]
