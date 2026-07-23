"""
NVD (National Vulnerability Database) API client.
Implements rate limiting, retry with exponential backoff, and response normalization.
API docs: https://nvd.nist.gov/developers/vulnerabilities
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings
from app.domain.exceptions import NVDAPIError, RateLimitError

logger = structlog.get_logger(__name__)


class NVDClient:
    """
    Async client for the NVD CVE API v2.

    Rate limits:
    - Without API key: 5 requests per 30 seconds
    - With API key: 50 requests per 30 seconds
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client: httpx.AsyncClient | None = None
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time: float = 0.0

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers: dict[str, str] = {
                "Accept": "application/json",
                "User-Agent": f"VulnAssessPlatform/{self._settings.app_version}",
            }
            if self._settings.nvd_api_key:
                headers["apiKey"] = self._settings.nvd_api_key

            self._client = httpx.AsyncClient(
                base_url=self._settings.nvd_api_base_url,
                headers=headers,
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
            )
        return self._client

    async def _respect_rate_limit(self) -> None:
        """Enforce NVD rate limits between requests."""
        async with self._rate_limit_lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request_time
            min_interval = self._settings.nvd_rate_limit_delay

            if elapsed < min_interval:
                sleep_time = min_interval - elapsed
                logger.debug("nvd_rate_limit_sleep", sleep_seconds=sleep_time)
                await asyncio.sleep(sleep_time)

            self._last_request_time = asyncio.get_event_loop().time()

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a GET request with rate limiting and retries."""
        await self._respect_rate_limit()

        client = self._get_client()
        try:
            response = await client.get("", params=params)
        except httpx.TimeoutException as e:
            raise NVDAPIError(f"Request timed out: {e}") from e
        except httpx.ConnectError as e:
            raise NVDAPIError(f"Connection failed: {e}") from e

        if response.status_code == 403:
            raise NVDAPIError("Invalid or missing API key", status_code=403)
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 30))
            raise RateLimitError(service="NVD", retry_after_seconds=retry_after)
        if response.status_code != 200:
            raise NVDAPIError(
                f"Unexpected status {response.status_code}: {response.text[:200]}",
                status_code=response.status_code,
            )

        return response.json()  # type: ignore[no-any-return]

    async def fetch_cve(self, cve_id: str) -> dict[str, Any] | None:
        """
        Fetch a single CVE by ID.

        Returns normalized CVE data dict or None if not found.
        """
        logger.info("nvd_fetch_cve", cve_id=cve_id)
        try:
            data = await self._get({"cveId": cve_id.upper()})
        except NVDAPIError as e:
            if e.status_code == 404:
                return None
            raise

        vulnerabilities = data.get("vulnerabilities", [])
        if not vulnerabilities:
            return None

        return self._normalize_cve(vulnerabilities[0].get("cve", {}))

    async def search_cves_by_keyword(
        self,
        keyword: str,
        results_per_page: int = 20,
    ) -> list[dict[str, Any]]:
        """Search CVEs by keyword (service name, product name, etc.)."""
        logger.info("nvd_search_cves", keyword=keyword)
        data = await self._get({
            "keywordSearch": keyword,
            "resultsPerPage": min(results_per_page, 100),
        })

        results = []
        for item in data.get("vulnerabilities", []):
            normalized = self._normalize_cve(item.get("cve", {}))
            if normalized:
                results.append(normalized)

        return results

    async def search_cves_by_cpe(self, cpe_name: str) -> list[dict[str, Any]]:
        """Search CVEs affecting a specific CPE (product)."""
        logger.info("nvd_search_by_cpe", cpe=cpe_name)
        data = await self._get({
            "cpeName": cpe_name,
            "resultsPerPage": 50,
        })

        results = []
        for item in data.get("vulnerabilities", []):
            normalized = self._normalize_cve(item.get("cve", {}))
            if normalized:
                results.append(normalized)
        return results

    def _normalize_cve(self, cve_data: dict[str, Any]) -> dict[str, Any] | None:
        """
        Normalize NVD API v2 response to our internal CVE schema.
        """
        if not cve_data:
            return None

        cve_id = cve_data.get("id", "")
        if not cve_id:
            return None

        # Extract English description
        descriptions = cve_data.get("descriptions", [])
        description = next(
            (d["value"] for d in descriptions if d.get("lang") == "en"),
            "No description available",
        )

        # Extract CVSS scores
        cvss_v3_score: float | None = None
        cvss_v3_vector: str | None = None
        cvss_v2_score: float | None = None

        metrics = cve_data.get("metrics", {})
        if cvss_v31 := metrics.get("cvssMetricV31", []):
            cvss_data = cvss_v31[0].get("cvssData", {})
            cvss_v3_score = cvss_data.get("baseScore")
            cvss_v3_vector = cvss_data.get("vectorString")
        elif cvss_v30 := metrics.get("cvssMetricV30", []):
            cvss_data = cvss_v30[0].get("cvssData", {})
            cvss_v3_score = cvss_data.get("baseScore")
            cvss_v3_vector = cvss_data.get("vectorString")

        if cvss_v2 := metrics.get("cvssMetricV2", []):
            cvss_v2_score = cvss_v2[0].get("cvssData", {}).get("baseScore")

        # Determine severity from CVSS score
        score = cvss_v3_score or cvss_v2_score or 0.0
        if score >= 9.0:
            severity = "critical"
        elif score >= 7.0:
            severity = "high"
        elif score >= 4.0:
            severity = "medium"
        elif score > 0:
            severity = "low"
        else:
            severity = "none"

        # Extract CPE configurations (affected products)
        affected_products: dict[str, Any] = {}
        configurations = cve_data.get("configurations", [])
        if configurations:
            affected_products["configurations"] = configurations[:5]  # Limit size

        # Extract references
        references = [
            {"url": ref.get("url"), "tags": ref.get("tags", [])}
            for ref in cve_data.get("references", [])[:10]
        ]

        # Extract CWEs
        weaknesses = cve_data.get("weaknesses", [])
        cwe_ids = [
            desc["value"]
            for weakness in weaknesses
            for desc in weakness.get("description", [])
            if desc.get("lang") == "en" and desc.get("value", "").startswith("CWE-")
        ]

        # Parse dates
        def parse_nvd_date(date_str: str | None) -> datetime | None:
            if not date_str:
                return None
            try:
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return None

        return {
            "cve_id": cve_id,
            "description": description,
            "cvss_v3_score": cvss_v3_score,
            "cvss_v3_vector": cvss_v3_vector,
            "cvss_v2_score": cvss_v2_score,
            "severity": severity,
            "affected_products": affected_products,
            "references": references,
            "cwe_ids": cwe_ids,
            "published_at": parse_nvd_date(cve_data.get("published")),
            "modified_at": parse_nvd_date(cve_data.get("lastModified")),
        }

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
