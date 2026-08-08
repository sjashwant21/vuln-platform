import pytest
from httpx import AsyncClient

from app.domain.enums import ScanStatus


@pytest.mark.asyncio
async def test_create_scan_job(
    client: AsyncClient,
    auth_headers: dict,
):
    """Test creating a new scan job."""

    payload = {
        "target_ips": ["8.8.8.8", "1.1.1.1"],
        "scan_type": "discovery",
        "scan_options": {"aggressiveness": "high"},
    }

    resp = await client.post("/v1/scans", json=payload, headers=auth_headers)
    assert resp.status_code == 201

    data = resp.json()
    assert data["status"] == ScanStatus.QUEUED.value
    assert data["target_ips"] == ["8.8.8.8/32", "1.1.1.1/32"]
    assert "id" in data


@pytest.mark.asyncio
async def test_list_scan_jobs(
    client: AsyncClient,
    auth_headers: dict,
):
    """Test listing scan jobs."""

    # Create one first
    payload = {"target_ips": ["8.8.8.8"], "scan_type": "discovery"}
    await client.post("/v1/scans", json=payload, headers=auth_headers)

    # List
    resp = await client.get("/v1/scans", headers=auth_headers)
    assert resp.status_code == 200

    data = resp.json()
    items = data.get("items", data) if isinstance(data, dict) else data
    assert len(items) >= 1
    assert items[0]["target_ips"] == ["8.8.8.8/32"]
