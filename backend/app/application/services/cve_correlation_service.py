"""
CVE correlation service — the intelligence engine core.

Input:  service name + version string
Output: IntelligenceReport with ranked CVE matches

Three-tier matching pipeline (run in parallel):

  Tier 1 — Cache scan
    Query local Postgres CVE cache with keyword search.
    Zero external calls, immediate results.
    Confidence: 0.6–1.0 depending on version match.

  Tier 2 — NVD keyword search
    POST to NVD with normalised service name.
    Catches CVEs not yet in local cache.
    Confidence: 0.7 (keyword match, no CPE confirmation).

  Tier 3 — NVD CPE search
    Construct likely CPE strings and query NVD.
    Highest fidelity — explicit product binding.
    Confidence: 0.9–1.0.

Results from all tiers are merged, deduplicated by CVE ID,
then passed through the risk scoring engine.
"""
from __future__ import annotations

import asyncio
import re
import time
from typing import Any

import structlog

from app.domain.models.cve import (
    CVE,
    CorrelationMatch,
    IntelligenceReport,
    MatchMethod,
    RiskContext,
)
from app.infrastructure.cache.cve_cache import CVECache
from app.infrastructure.cve.nvd_client import NVDClient
from app.infrastructure.cve.version_matcher import VersionMatcher

logger = structlog.get_logger(__name__)


class CVECorrelationService:
    """
    Orchestrates CVE lookup, correlation, and risk scoring.

    Injected dependencies:
      nvd_client      — live NVD API access
      cve_cache       — two-layer cache (Redis + Postgres)
      version_matcher — CPE/version comparison logic
    """

    def __init__(
        self,
        nvd_client:      NVDClient,
        cve_cache:       CVECache,
        version_matcher: VersionMatcher,
    ) -> None:
        self._nvd     = nvd_client
        self._cache   = cve_cache
        self._matcher = version_matcher

    # ── Public interface ───────────────────────────────────────

    async def correlate(
        self,
        service:       str,
        version:       str,
        risk_context:  RiskContext | None = None,
        max_results:   int = 50,
        use_live_nvd:  bool = True,
    ) -> IntelligenceReport:
        """
        Main entry point. Returns a fully scored IntelligenceReport.

        Args:
            service:      Service/software name (e.g. "apache httpd", "nginx")
            version:      Version string (e.g. "2.4.51", "1.18.0")
            risk_context: Asset-specific context for risk score adjustment
            max_results:  Cap on number of CVE matches to return
            use_live_nvd: If False, cache-only mode (faster, may miss recent CVEs)
        """
        t0 = time.perf_counter()

        if not service.strip() or not version.strip():
            return IntelligenceReport(
                service=service,
                version=version,
                query_time_ms=0.0,
                matches=(),
            )

        ctx = risk_context or RiskContext()

        logger.info(
            "cve_correlation_start",
            service=service,
            version=version,
            use_live_nvd=use_live_nvd,
        )

        # ── Parallel tier execution ────────────────────────────
        if use_live_nvd:
            cache_task   = asyncio.create_task(self._tier_cache(service, version))
            keyword_task = asyncio.create_task(self._tier_keyword(service, version))
            cpe_task     = asyncio.create_task(self._tier_cpe(service, version))

            tier_results = await asyncio.gather(
                cache_task,
                keyword_task,
                cpe_task,
                return_exceptions=True,
            )
        else:
            cache_result = await self._tier_cache(service, version)
            tier_results = [cache_result, [], []]

        # ── Merge and deduplicate ──────────────────────────────
        all_matches = self._merge_results(tier_results, service, version)

        # ── Risk scoring ───────────────────────────────────────
        scored = [
            self._score_match(match, ctx)
            for match in all_matches
        ]

        # ── Sort and cap ───────────────────────────────────────
        scored.sort(key=lambda m: m.risk_score, reverse=True)
        scored = scored[:max_results]

        elapsed_ms = (time.perf_counter() - t0) * 1000

        report = IntelligenceReport(
            service=service,
            version=version,
            query_time_ms=round(elapsed_ms, 2),
            matches=tuple(scored),
        )

        logger.info(
            "cve_correlation_complete",
            service=service,
            version=version,
            total_matches=report.total_findings,
            critical=report.critical_count,
            high=report.high_count,
            elapsed_ms=round(elapsed_ms, 1),
        )

        return report

    async def correlate_batch(
        self,
        targets: list[dict[str, str]],
        risk_context: RiskContext | None = None,
    ) -> list[IntelligenceReport]:
        """
        Correlate multiple (service, version) pairs.
        Uses bounded concurrency to avoid hammering NVD.
        """
        semaphore = asyncio.Semaphore(3)   # max 3 concurrent NVD queries

        async def _bounded(target: dict[str, str]) -> IntelligenceReport:
            async with semaphore:
                return await self.correlate(
                    service=target.get("service", ""),
                    version=target.get("version", ""),
                    risk_context=risk_context,
                )

        tasks = [asyncio.create_task(_bounded(t)) for t in targets]
        return list(await asyncio.gather(*tasks, return_exceptions=False))

    # ── Tier 1: Local cache ────────────────────────────────────

    async def _tier_cache(
        self,
        service: str,
        version: str,
    ) -> list[CorrelationMatch]:
        try:
            cached_cves = await self._cache.search_cached(service, limit=100)
            matches = []
            for cve in cached_cves:
                score = self._matcher.score_cpe_list(
                    service=service,
                    version=version,
                    cpe_strings=cve.cpe_matches,
                )
                if score >= 0.3:
                    matches.append(
                        CorrelationMatch(
                            cve=             cve,
                            match_method=    MatchMethod.CACHE_HIT,
                            matched_version= version,
                            matched_service= service,
                            confidence=      score,
                        )
                    )
            logger.debug("tier_cache_complete", count=len(matches))
            return matches
        except Exception as exc:
            logger.warning("tier_cache_error", error=str(exc))
            return []

    # ── Tier 2: NVD keyword search ─────────────────────────────

    async def _tier_keyword(
        self,
        service: str,
        version: str,
    ) -> list[CorrelationMatch]:
        try:
            # Search with service + version for precision
            keyword = f"{service} {version}"
            cves = await self._nvd.search_by_keyword(keyword, max_results=30)

            # Also search service-only for broader coverage
            cves_broad = await self._nvd.search_by_keyword(service, max_results=30)

            all_cves = {c.cve_id: c for c in cves + cves_broad}

            matches = []
            for cve in all_cves.values():
                # Backfill cache
                await self._cache.set(cve)

                score = self._matcher.score_cpe_list(
                    service=service,
                    version=version,
                    cpe_strings=cve.cpe_matches,
                )
                confidence = max(0.5, score) if score > 0 else 0.7

                matches.append(
                    CorrelationMatch(
                        cve=             cve,
                        match_method=    MatchMethod.KEYWORD,
                        matched_version= version,
                        matched_service= service,
                        confidence=      confidence,
                    )
                )

            logger.debug("tier_keyword_complete", count=len(matches))
            return matches
        except Exception as exc:
            logger.warning("tier_keyword_error", error=str(exc))
            return []

    # ── Tier 3: NVD CPE search ─────────────────────────────────

    async def _tier_cpe(
        self,
        service: str,
        version: str,
    ) -> list[CorrelationMatch]:
        """
        Generate candidate CPE strings and search NVD with each.
        CPE format: cpe:2.3:a:{vendor}:{product}:{version}:*:*:*:*:*:*:*
        """
        try:
            candidate_cpes = self._build_cpe_candidates(service, version)
            if not candidate_cpes:
                return []

            all_cves: dict[str, CVE] = {}
            for cpe in candidate_cpes[:3]:   # cap CPE searches to 3
                try:
                    cves = await self._nvd.search_by_cpe(cpe, max_results=50)
                    for cve in cves:
                        all_cves[cve.cve_id] = cve
                        await self._cache.set(cve)
                except Exception as exc:
                    logger.debug("cpe_search_error", cpe=cpe, error=str(exc))

            matches = []
            for cve in all_cves.values():
                score = self._matcher.score_cpe_list(
                    service=service,
                    version=version,
                    cpe_strings=cve.cpe_matches,
                )
                if score >= 0.4:
                    matches.append(
                        CorrelationMatch(
                            cve=             cve,
                            match_method=    (
                                MatchMethod.CPE_EXACT
                                if score >= 0.9 else MatchMethod.VERSION_RANGE
                            ),
                            matched_version= version,
                            matched_service= service,
                            confidence=      score,
                        )
                    )

            logger.debug("tier_cpe_complete", count=len(matches), cpes=candidate_cpes[:3])
            return matches
        except Exception as exc:
            logger.warning("tier_cpe_error", error=str(exc))
            return []

    @staticmethod
    def _build_cpe_candidates(service: str, version: str) -> list[str]:
        """
        Generate plausible CPE 2.3 strings for a (service, version) pair.
        We can't know the exact vendor/product without a CPE dictionary,
        so we generate variations and let NVD match.
        """
        name_clean = service.lower().strip()
        name_cpe   = re.sub(r"[^a-z0-9]", "_", name_clean).strip("_")
        ver_clean  = version.lower().strip().lstrip("v")

        # Common vendor guesses for well-known services
        _VENDOR_MAP: dict[str, str] = {
            "nginx":       "nginx",
            "apache":      "apache",
            "httpd":       "apache",
            "http_server": "apache",
            "openssh":     "openbsd",
            "openssl":     "openssl",
            "mysql":       "oracle",
            "mariadb":     "mariadb",
            "postgresql":  "postgresql",
            "redis":       "redis",
            "tomcat":      "apache",
            "php":         "php",
            "python":      "python",
            "nodejs":      "nodejs",
            "wordpress":   "wordpress",
            "vsftpd":      "vsftpd_project",
        }

        vendor = _VENDOR_MAP.get(name_cpe, name_cpe)

        candidates = []
        # Exact version CPE
        candidates.append(f"cpe:2.3:a:{vendor}:{name_cpe}:{ver_clean}:*:*:*:*:*:*:*")
        # Any-version CPE (wildcard — returns all CVEs for the product)
        candidates.append(f"cpe:2.3:a:{vendor}:{name_cpe}:*:*:*:*:*:*:*:*")

        # Handle "apache httpd" → try both "apache:http_server" and "apache:httpd"
        if " " in name_clean:
            parts  = name_clean.split()
            vendor_alt  = re.sub(r"[^a-z0-9]", "_", parts[0])
            product_alt = re.sub(r"[^a-z0-9]", "_", "_".join(parts[1:]))
            candidates.append(
                f"cpe:2.3:a:{vendor_alt}:{product_alt}:{ver_clean}:*:*:*:*:*:*:*"
            )

        return candidates

    # ── Merge and dedup ────────────────────────────────────────

    @staticmethod
    def _merge_results(
        tier_results: list[Any],
        service:      str,
        version:      str,
    ) -> list[CorrelationMatch]:
        """
        Merge results from all tiers, keeping the highest-confidence
        match when the same CVE appears in multiple tiers.
        """
        best: dict[str, CorrelationMatch] = {}

        for tier_result in tier_results:
            if isinstance(tier_result, Exception):
                logger.warning("tier_exception", error=str(tier_result))
                continue
            if not isinstance(tier_result, list):
                continue
            for match in tier_result:
                existing = best.get(match.cve_id)
                if existing is None or match.confidence > existing.confidence:
                    best[match.cve_id] = match

        return list(best.values())

    # ── Risk scoring ───────────────────────────────────────────

    def _score_match(
        self,
        match: CorrelationMatch,
        ctx:   RiskContext,
    ) -> CorrelationMatch:
        """
        Compute a business-adjusted risk score (0.0 – 10.0).

        Formula:
          base    = CVSS base score (or 5.0 if unknown)
          × criticality_multiplier (0.7 – 1.5)
          × exposure_factor        (1.0 – 1.3)
          × exploit_factor         (1.0 – 1.3)
          × confidence             (0.3 – 1.0)
          → capped at 10.0
        """
        cve   = match.cve
        cvss  = cve.base_score or 5.0    # default to medium if unknown

        criticality_mult = ctx.asset_criticality.multiplier
        exposure_factor  = 1.3 if ctx.internet_exposed else 1.0
        exploit_factor   = 1.3 if cve.has_public_exploit else 1.0

        # Network-exploitable CVEs get additional weight
        if cve.cvss_v3 and cve.cvss_v3.is_network_exploitable:
            exploit_factor = min(1.5, exploit_factor + 0.2)

        raw_risk = (
            cvss
            * criticality_mult
            * exposure_factor
            * exploit_factor
            * match.confidence
        )
        risk_score = round(min(10.0, raw_risk), 2)

        # Return a new frozen CorrelationMatch with the risk score set
        return CorrelationMatch(
            cve=             cve,
            match_method=    match.match_method,
            matched_version= match.matched_version,
            matched_service= match.matched_service,
            confidence=      match.confidence,
            risk_score=      risk_score,
        )

