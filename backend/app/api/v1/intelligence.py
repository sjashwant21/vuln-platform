"""
Vulnerability intelligence API router — /v1/intelligence/*

Endpoints:
  POST /v1/intelligence/correlate          Single service/version lookup
  POST /v1/intelligence/correlate/batch    Batch lookup (up to 20 targets)
  GET  /v1/intelligence/cve/{cve_id}       Direct CVE lookup by ID
  POST /v1/intelligence/rescore            Re-score a CVE with different context
  GET  /v1/intelligence/status             Ingestion pipeline status

All routes require authentication.
Rate limiting enforced by SlowAPI (per-user, not per-IP).
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas.cve_schemas import (
    BatchCorrelateRequest,
    BatchReportResponse,
    CorrelateRequest,
    CVEDetailResponse,
    CVEReferenceResponse,
    CVEResponse,
    CVSSMetricsResponse,
    IngestionStatusResponse,
    IntelligenceReportResponse,
    report_to_response,
)
from app.dependencies import CurrentUser
from app.domain.models.cve import AssetCriticality, RiskContext

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/intelligence", tags=["Vulnerability Intelligence"])


# ── Dependency: build the correlation service per request ──────

def _get_correlation_service(
    db: Annotated[object, Depends(lambda: None)],   # replaced below
) -> object:
    pass   # placeholder — see actual dep below


async def _build_correlation_service(
    request: object,
) -> CVECorrelationService:  # type: ignore[name-defined]  # noqa: F821
    """
    Build the correlation service with per-request Redis and DB session.
    In production this is provided by the DI container in dependencies.py.
    This inline version is used here to keep the router self-contained.
    """
    import redis.asyncio as aioredis

    from app.application.services.cve_correlation_service import CVECorrelationService
    from app.config import get_settings
    from app.infrastructure.cache.cve_cache import CVECache
    from app.infrastructure.cache.rate_limiter import RedisTokenBucket
    from app.infrastructure.cve.nvd_client import NVDClient
    from app.infrastructure.cve.version_matcher import VersionMatcher
    from app.infrastructure.database.connection import get_session_factory

    cfg = get_settings()

    redis_client = aioredis.from_url(cfg.redis_url, encoding="utf-8", decode_responses=True)

    capacity     = 50.0 if cfg.nvd_api_key else 5.0
    rate_limiter = RedisTokenBucket(
        redis=redis_client,
        key="nvd_api_global",
        capacity=capacity,
        refill_rate=capacity / 30.0,
    )

    nvd_client = NVDClient(rate_limiter=rate_limiter)

    # Get a session from the factory (not the per-request DI session)
    factory = get_session_factory()
    session = factory()

    cache   = CVECache(redis=redis_client, session=session)
    matcher = VersionMatcher()

    return CVECorrelationService(
        nvd_client=nvd_client,
        cve_cache=cache,
        version_matcher=matcher,
    ), session, redis_client, nvd_client


# ── POST /intelligence/correlate ───────────────────────────────

@router.post(
    "/correlate",
    response_model=IntelligenceReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Correlate a service and version against the CVE database",
    description="""
Queries the NVD API and local CVE cache to find all known vulnerabilities
affecting the specified service and version.

Returns CVEs with CVSS scores, severity ratings, risk scores adjusted for
your asset context, and remediation references.

**Rate limit:** 10 requests/minute per user.
    """,
)
async def correlate(
    body:         CorrelateRequest,
    current_user: CurrentUser,
) -> IntelligenceReportResponse:
    import redis.asyncio as aioredis

    from app.application.services.cve_correlation_service import CVECorrelationService
    from app.config import get_settings
    from app.infrastructure.cache.cve_cache import CVECache
    from app.infrastructure.cache.rate_limiter import RedisTokenBucket
    from app.infrastructure.cve.nvd_client import NVDClient
    from app.infrastructure.cve.version_matcher import VersionMatcher
    from app.infrastructure.database.connection import get_session_factory

    cfg = get_settings()

    redis_client = aioredis.from_url(
        cfg.redis_url, encoding="utf-8", decode_responses=True
    )

    try:
        capacity     = 50.0 if cfg.nvd_api_key else 5.0
        rate_limiter = RedisTokenBucket(
            redis=redis_client,
            key="nvd_api_global",
            capacity=capacity,
            refill_rate=capacity / 30.0,
        )
        nvd_client = NVDClient(rate_limiter=rate_limiter)

        ctx = RiskContext(
            asset_criticality=AssetCriticality(body.asset_criticality),
            internet_exposed=body.internet_exposed,
        )

        factory = get_session_factory()
        async with factory() as session:
            cache   = CVECache(redis=redis_client, session=session)
            matcher = VersionMatcher()
            svc     = CVECorrelationService(
                nvd_client=nvd_client,
                cve_cache=cache,
                version_matcher=matcher,
            )

            report = await svc.correlate(
                service=      body.service,
                version=      body.version,
                risk_context= ctx,
                max_results=  body.max_results,
                use_live_nvd= body.use_live_nvd,
            )
            await session.commit()

        logger.info(
            "correlate_request",
            org_id=current_user.org_id,
            service=body.service,
            version=body.version,
            findings=report.total_findings,
        )

        return report_to_response(report)

    finally:
        await redis_client.aclose()
        await nvd_client.close()


# ── POST /intelligence/correlate/batch ────────────────────────

@router.post(
    "/correlate/batch",
    response_model=BatchReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch CVE correlation for multiple service/version pairs",
)
async def correlate_batch(
    body:         BatchCorrelateRequest,
    current_user: CurrentUser,
) -> BatchReportResponse:
    import redis.asyncio as aioredis

    from app.application.services.cve_correlation_service import CVECorrelationService
    from app.config import get_settings
    from app.infrastructure.cache.cve_cache import CVECache
    from app.infrastructure.cache.rate_limiter import RedisTokenBucket
    from app.infrastructure.cve.nvd_client import NVDClient
    from app.infrastructure.cve.version_matcher import VersionMatcher
    from app.infrastructure.database.connection import get_session_factory

    cfg = get_settings()
    redis_client = aioredis.from_url(
        cfg.redis_url, encoding="utf-8", decode_responses=True
    )

    try:
        capacity     = 50.0 if cfg.nvd_api_key else 5.0
        rate_limiter = RedisTokenBucket(
            redis=redis_client,
            key="nvd_api_global",
            capacity=capacity,
            refill_rate=capacity / 30.0,
        )
        nvd_client = NVDClient(rate_limiter=rate_limiter)
        ctx = RiskContext(
            asset_criticality=AssetCriticality(body.asset_criticality),
            internet_exposed=body.internet_exposed,
        )

        factory = get_session_factory()
        async with factory() as session:
            cache   = CVECache(redis=redis_client, session=session)
            matcher = VersionMatcher()
            svc     = CVECorrelationService(
                nvd_client=nvd_client,
                cve_cache=cache,
                version_matcher=matcher,
            )

            targets = [
                {"service": t.service, "version": t.version}
                for t in body.targets
            ]

            reports = await svc.correlate_batch(targets, risk_context=ctx)
            await session.commit()

        responses = [report_to_response(r) for r in reports]
        total_findings = sum(r.total_findings for r in responses)

        logger.info(
            "batch_correlate_request",
            org_id=current_user.org_id,
            targets=len(targets),
            total_findings=total_findings,
        )

        return BatchReportResponse(
            total_targets=len(responses),
            total_findings=total_findings,
            reports=responses,
        )

    finally:
        await redis_client.aclose()
        await nvd_client.close()


# ── GET /intelligence/cve/{cve_id} ────────────────────────────

@router.get(
    "/cve/{cve_id}",
    response_model=CVEDetailResponse,
    summary="Fetch a single CVE by ID",
    description="Looks up a CVE by ID from local cache first, then NVD if not cached.",
)
async def get_cve(
    cve_id:       str,
    current_user: CurrentUser,
) -> CVEDetailResponse:
    import re

    import redis.asyncio as aioredis

    from app.config import get_settings
    from app.infrastructure.cache.cve_cache import CVECache
    from app.infrastructure.cache.rate_limiter import RedisTokenBucket
    from app.infrastructure.cve.nvd_client import NVDClient
    from app.infrastructure.database.connection import get_session_factory

    if not re.match(r"^CVE-\d{4}-\d{4,}$", cve_id.upper()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"'{cve_id}' is not a valid CVE identifier",
        )

    cfg = get_settings()
    cve_id = cve_id.upper()

    redis_client = aioredis.from_url(
        cfg.redis_url, encoding="utf-8", decode_responses=True
    )

    try:
        capacity     = 50.0 if cfg.nvd_api_key else 5.0
        rate_limiter = RedisTokenBucket(
            redis=redis_client,
            key="nvd_api_global",
            capacity=capacity,
            refill_rate=capacity / 30.0,
        )
        nvd_client = NVDClient(rate_limiter=rate_limiter)
        factory    = get_session_factory()

        async with factory() as session:
            cache  = CVECache(redis=redis_client, session=session)
            cve    = await cache.get(cve_id)
            cached = cve is not None

            if cve is None:
                # Not in cache — fetch from NVD
                cve = await nvd_client.fetch_cve(cve_id)
                if cve is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"CVE '{cve_id}' not found in NVD",
                    )
                await cache.set(cve)
                await session.commit()

        # Build response
        cvss_v3 = None
        if cve.cvss_v3:
            cvss_v3 = CVSSMetricsResponse(
                version=              cve.cvss_v3.version,
                base_score=           cve.cvss_v3.base_score,
                vector_string=        cve.cvss_v3.vector_string,
                severity=             cve.cvss_v3.severity.value,
                attack_vector=        cve.cvss_v3.attack_vector,
                attack_complexity=    cve.cvss_v3.attack_complexity,
                privileges_required=  cve.cvss_v3.privileges_required,
                user_interaction=     cve.cvss_v3.user_interaction,
                is_network_exploitable=cve.cvss_v3.is_network_exploitable,
                requires_no_privileges=cve.cvss_v3.requires_no_privileges,
            )

        refs = [
            CVEReferenceResponse(
                url=r.url, tags=list(r.tags),
                is_patch=r.is_patch(), is_exploit=r.is_exploit()
            )
            for r in cve.references
        ]

        cve_resp = CVEResponse(
            cve_id=           cve.cve_id,
            description=      cve.description,
            severity=         cve.severity.value,
            cvss_v3=          cvss_v3,
            base_score=       cve.base_score,
            cwe_ids=          list(cve.cwe_ids),
            references=       refs,
            published_at=     cve.published_at,
            has_public_exploit=cve.has_public_exploit,
            has_patch=        cve.has_patch,
        )

        return CVEDetailResponse(cve=cve_resp, cached=cached)

    finally:
        await redis_client.aclose()
        await nvd_client.close()


# ── GET /intelligence/status ───────────────────────────────────

@router.get(
    "/status",
    response_model=IngestionStatusResponse,
    summary="CVE ingestion pipeline status",
)
async def ingestion_status(
    current_user: CurrentUser,
) -> IngestionStatusResponse:
    from datetime import timedelta

    import redis.asyncio as aioredis
    from sqlalchemy import func, select

    from app.config import get_settings
    from app.infrastructure.cache.rate_limiter import RedisTokenBucket
    from app.infrastructure.database.connection import get_session_factory
    from app.infrastructure.database.models import CVECacheModel

    cfg = get_settings()
    redis_client = aioredis.from_url(
        cfg.redis_url, encoding="utf-8", decode_responses=True
    )

    try:
        capacity     = 50.0 if cfg.nvd_api_key else 5.0
        rate_limiter = RedisTokenBucket(
            redis=redis_client,
            key="nvd_api_global",
            capacity=capacity,
            refill_rate=capacity / 30.0,
        )
        tokens = await rate_limiter.current_tokens()

        factory = get_session_factory()
        async with factory() as session:
            total = (
                await session.execute(select(func.count()).select_from(CVECacheModel))
            ).scalar_one()

            cutoff = datetime.now(UTC) - timedelta(hours=24)
            stale = (
                await session.execute(
                    select(func.count())
                    .select_from(CVECacheModel)
                    .where(CVECacheModel.synced_at < cutoff)
                )
            ).scalar_one()

        return IngestionStatusResponse(
            total_cached_cves=total,
            stale_count=stale,
            redis_token_remaining=round(tokens, 1),
        )

    finally:
        await redis_client.aclose()
