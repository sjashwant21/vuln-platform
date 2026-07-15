"""
NVD CVE API v2 client.

Design principles:
  1. Rate limiter checked before EVERY request (shared Redis bucket)
  2. Retry with exponential backoff + jitter on transient errors
  3. All NVD JSON → CVE domain objects here — never leaks raw JSON upstream
  4. Comprehensive error classification: don't retry 403/404, do retry 503/429
  5. Pagination handled transparently — callers get a flat list

NVD API limits (June 2025):
  Without API key: 5 requests / 30 seconds
  With API key:    50 requests / 30 seconds
  Max results per page: 2000

Reference: https://nvd.nist.gov/developers/vulnerabilities
"""
from __future__ import annotations

import asyncio
import random
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog

from app.config import get_settings
from app.domain.exceptions import NVDAPIError, RateLimitError
from app.domain.models.cve import CVE, CVSSMetrics, CVEReference
from app.infrastructure.cache.rate_limiter import RedisTokenBucket

logger = structlog.get_logger(__name__)

_NVD_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"
_MAX_PAGE  = 2000    # NVD hard limit per page
_JITTER    = 0.5     # ±0.5s random jitter on retries


class NVDClient:
    """
    Async NVD API v2 client.

    Instantiate once per worker process. The rate limiter is Redis-backed,
    so multiple instances across processes share the same token bucket.
    """

    def __init__(self, rate_limiter: RedisTokenBucket) -> None:
        self._cfg     = get_settings()
        self._limiter = rate_limiter
        self._http: httpx.AsyncClient | None = None

    def _client(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            headers: dict[str, str] = {
                "User-Agent": f"VulnAssess/{self._cfg.app_version} (security-research)",
                "Accept":     "application/json",
            }
            if self._cfg.nvd_api_key:
                headers["apiKey"] = self._cfg.nvd_api_key

            self._http = httpx.AsyncClient(
                base_url=_NVD_BASE,
                headers=headers,
                timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=5.0),
                follow_redirects=True,
                http2=False,          # NVD doesn't support h2
            )
        return self._http

    # ── Public API ─────────────────────────────────────────────

    async def fetch_cve(self, cve_id: str) -> CVE | None:
        """
        Fetch a single CVE by ID.
        Returns None if NVD has no record for this ID.
        """
        logger.debug("nvd_fetch_cve", cve_id=cve_id)
        data = await self._get({"cveId": cve_id.upper()})
        vulns = data.get("vulnerabilities", [])
        if not vulns:
            return None
        return self._parse_item(vulns[0])

    async def search_by_keyword(
        self,
        keyword:      str,
        max_results:  int = 50,
        published_after: datetime | None = None,
    ) -> list[CVE]:
        """
        Search NVD by keyword — used when we don't have an exact CPE.
        Paginates automatically up to max_results.
        """
        logger.info("nvd_keyword_search", keyword=keyword, max_results=max_results)

        params: dict[str, Any] = {
            "keywordSearch":  keyword,
            "keywordExactMatch": "",    # NVD flag for exact phrase match
        }
        if published_after:
            params["pubStartDate"] = published_after.strftime("%Y-%m-%dT%H:%M:%S.000")

        return await self._paginate(params, max_results)

    async def search_by_cpe(
        self,
        cpe_name:    str,
        max_results: int = 100,
    ) -> list[CVE]:
        """
        Search CVEs affecting a specific CPE product string.
        Most precise matching method when CPE is known.
        """
        logger.info("nvd_cpe_search", cpe=cpe_name[:80])
        params: dict[str, Any] = {
            "cpeName":    cpe_name,
            "isExact":    "",
        }
        return await self._paginate(params, max_results)

    async def fetch_recent(
        self,
        hours_back: int = 2,
        max_results: int = 500,
    ) -> list[CVE]:
        """
        Fetch CVEs modified in the last N hours.
        Used by the background incremental sync task.
        """
        from datetime import timedelta
        now = datetime.now(UTC)
        start = now - timedelta(hours=hours_back)

        params: dict[str, Any] = {
            "lastModStartDate": start.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "lastModEndDate":   now.strftime("%Y-%m-%dT%H:%M:%S.000"),
        }
        logger.info(
            "nvd_fetch_recent",
            hours_back=hours_back,
            start=start.isoformat(),
        )
        return await self._paginate(params, max_results)

    # ── Pagination ─────────────────────────────────────────────

    async def _paginate(
        self,
        base_params: dict[str, Any],
        max_results: int,
    ) -> list[CVE]:
        """
        Transparently paginate NVD responses.
        NVD returns resultsPerPage and totalResults — we loop until done.
        """
        results: list[CVE] = []
        start_index = 0
        page_size   = min(_MAX_PAGE, max_results)

        while len(results) < max_results:
            params = {
                **base_params,
                "resultsPerPage": page_size,
                "startIndex":     start_index,
            }

            data = await self._get(params)
            total     = data.get("totalResults", 0)
            page_data = data.get("vulnerabilities", [])

            for item in page_data:
                cve = self._parse_item(item)
                if cve:
                    results.append(cve)

            fetched_so_far = start_index + len(page_data)
            if fetched_so_far >= total or not page_data:
                break

            start_index += len(page_data)
            # NVD recommends a short sleep between paginated requests
            await asyncio.sleep(0.6)

        logger.debug("nvd_paginate_complete", total_fetched=len(results))
        return results[:max_results]

    # ── HTTP layer ─────────────────────────────────────────────

    async def _get(
        self,
        params: dict[str, Any],
        *,
        attempt: int = 0,
    ) -> dict[str, Any]:
        """
        Execute one GET with rate limiting and retry logic.

        Retry policy:
          - 429 / 503: exponential backoff, max 3 retries
          - 403:       raise immediately (bad API key)
          - 404:       raise immediately (not found)
          - Timeout:   retry up to 3 times
        """
        max_attempts = 4

        # Acquire rate-limit token (blocks if necessary)
        await self._limiter.acquire()

        try:
            response = await self._client().get("", params=params)
        except httpx.TimeoutException as exc:
            if attempt < max_attempts:
                wait = self._backoff(attempt)
                logger.warning("nvd_timeout_retry", attempt=attempt, wait_s=wait)
                await asyncio.sleep(wait)
                return await self._get(params, attempt=attempt + 1)
            raise NVDAPIError(f"Request timed out after {max_attempts} attempts") from exc
        except httpx.ConnectError as exc:
            if attempt < max_attempts:
                wait = self._backoff(attempt)
                await asyncio.sleep(wait)
                return await self._get(params, attempt=attempt + 1)
            raise NVDAPIError(f"Connection failed: {exc}") from exc

        # ── Status code handling ───────────────────────────────
        if response.status_code == 200:
            try:
                return response.json()  # type: ignore[no-any-return]
            except Exception as exc:
                raise NVDAPIError(f"Invalid JSON in response: {exc}") from exc

        if response.status_code == 403:
            raise NVDAPIError("API key invalid or missing", status_code=403)

        if response.status_code == 404:
            return {"vulnerabilities": [], "totalResults": 0}

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 30))
            if attempt < max_attempts:
                wait = max(retry_after, self._backoff(attempt))
                logger.warning("nvd_rate_limited", retry_after=retry_after, wait=wait)
                await asyncio.sleep(wait)
                return await self._get(params, attempt=attempt + 1)
            raise RateLimitError("NVD", retry_after_seconds=retry_after)

        if response.status_code in (500, 502, 503, 504):
            if attempt < max_attempts:
                wait = self._backoff(attempt)
                logger.warning(
                    "nvd_server_error_retry",
                    status=response.status_code,
                    attempt=attempt,
                    wait=wait,
                )
                await asyncio.sleep(wait)
                return await self._get(params, attempt=attempt + 1)

        raise NVDAPIError(
            f"NVD returned {response.status_code}: {response.text[:200]}",
            status_code=response.status_code,
        )

    @staticmethod
    def _backoff(attempt: int) -> float:
        """Exponential backoff with ±0.5s jitter."""
        base  = min(30.0, 2 ** attempt)
        jitter = random.uniform(-_JITTER, _JITTER)
        return max(0.5, base + jitter)

    # ── Response normalisation ─────────────────────────────────

    def _parse_item(self, item: dict[str, Any]) -> CVE | None:
        """
        Normalise one NVD vulnerability item into a CVE domain object.
        Returns None if the item is missing required fields.
        """
        cve_data = item.get("cve", {})
        if not cve_data:
            return None

        cve_id = cve_data.get("id", "")
        if not cve_id:
            return None

        description = self._extract_description(cve_data)
        cvss_v3     = self._extract_cvss_v3(cve_data)
        cvss_v2     = self._extract_cvss_v2(cve_data)
        references  = self._extract_references(cve_data)
        cwe_ids     = self._extract_cwes(cve_data)
        cpe_matches = self._extract_cpes(cve_data)

        published_at = self._parse_nvd_date(cve_data.get("published"))
        modified_at  = self._parse_nvd_date(cve_data.get("lastModified"))

        return CVE(
            cve_id=      cve_id,
            description= description,
            published_at=published_at,
            modified_at= modified_at,
            cvss_v3=     cvss_v3,
            cvss_v2=     cvss_v2,
            cwe_ids=     tuple(cwe_ids),
            references=  tuple(references),
            cpe_matches= tuple(cpe_matches),
        )

    @staticmethod
    def _extract_description(cve_data: dict[str, Any]) -> str:
        descs = cve_data.get("descriptions", [])
        for d in descs:
            if d.get("lang") == "en":
                return d.get("value", "No description available")
        return descs[0].get("value", "No description available") if descs else ""

    @staticmethod
    def _extract_cvss_v3(cve_data: dict[str, Any]) -> CVSSMetrics | None:
        metrics = cve_data.get("metrics", {})

        for key in ("cvssMetricV31", "cvssMetricV30"):
            entries = metrics.get(key, [])
            if not entries:
                continue
            # Prefer "Primary" source
            primary = next(
                (e for e in entries if e.get("type") == "Primary"),
                entries[0],
            )
            d = primary.get("cvssData", {})
            if not d:
                continue
            version = "3.1" if key == "cvssMetricV31" else "3.0"
            return CVSSMetrics(
                version=             version,
                base_score=          float(d.get("baseScore", 0)),
                vector_string=       d.get("vectorString", ""),
                attack_vector=       d.get("attackVector"),
                attack_complexity=   d.get("attackComplexity"),
                privileges_required= d.get("privilegesRequired"),
                user_interaction=    d.get("userInteraction"),
                scope=               d.get("scope"),
                confidentiality=     d.get("confidentialityImpact"),
                integrity=           d.get("integrityImpact"),
                availability=        d.get("availabilityImpact"),
            )
        return None

    @staticmethod
    def _extract_cvss_v2(cve_data: dict[str, Any]) -> CVSSMetrics | None:
        entries = cve_data.get("metrics", {}).get("cvssMetricV2", [])
        if not entries:
            return None
        d = entries[0].get("cvssData", {})
        if not d:
            return None
        return CVSSMetrics(
            version=      "2.0",
            base_score=   float(d.get("baseScore", 0)),
            vector_string=d.get("vectorString", ""),
            attack_vector=d.get("accessVector"),
            attack_complexity=d.get("accessComplexity"),
        )

    @staticmethod
    def _extract_references(cve_data: dict[str, Any]) -> list[CVEReference]:
        refs = []
        for r in cve_data.get("references", [])[:20]:   # cap to avoid huge payloads
            url  = r.get("url", "")
            tags = tuple(r.get("tags", []))
            if url:
                refs.append(CVEReference(url=url, tags=tags))
        return refs

    @staticmethod
    def _extract_cwes(cve_data: dict[str, Any]) -> list[str]:
        cwes = []
        for weakness in cve_data.get("weaknesses", []):
            for desc in weakness.get("description", []):
                val = desc.get("value", "")
                if val.startswith("CWE-"):
                    cwes.append(val)
        return cwes

    @staticmethod
    def _extract_cpes(cve_data: dict[str, Any]) -> list[str]:
        """Extract all CPE 2.3 strings from the NVD configuration nodes."""
        cpes: list[str] = []
        for config in cve_data.get("configurations", []):
            for node in config.get("nodes", []):
                for match in node.get("cpeMatch", []):
                    if match.get("vulnerable"):
                        cpe = match.get("criteria", "")
                        if cpe:
                            cpes.append(cpe)
        return cpes

    @staticmethod
    def _parse_nvd_date(date_str: str | None) -> datetime | None:
        if not date_str:
            return None
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
            try:
                dt = datetime.strptime(date_str[:26], fmt)
                return dt.replace(tzinfo=UTC)
            except ValueError:
                continue
        return None

    async def close(self) -> None:
        if self._http and not self._http.is_closed:
            await self._http.aclose()
