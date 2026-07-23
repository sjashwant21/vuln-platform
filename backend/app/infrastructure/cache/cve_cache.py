"""
Two-layer CVE cache: Redis (hot) → PostgreSQL (warm) → NVD (cold).

Layer 1 — Redis (TTL: 4 hours)
  Serialised CVE domain objects. Sub-millisecond reads.
  Avoids hitting Postgres for repeated queries within a work session.

Layer 2 — PostgreSQL cve_cache table (TTL: 24 hours based on synced_at)
  Persists across Redis eviction and process restarts.
  Source of truth for the background sync worker.

Callers never know which layer served the response —
they call get() and receive a CVE | None.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import redis.asyncio as aioredis
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.cve import (
    CVE,
    CVEReference,
    CVSSMetrics,
)

logger = structlog.get_logger(__name__)

_REDIS_TTL_SECONDS = 4 * 3600       # 4 hours in hot cache
_PG_STALE_HOURS    = 24             # re-fetch from NVD after 24h


class CVECache:
    """
    Read-through cache for CVE records.

    Constructor takes both a Redis client and a SQLAlchemy session.
    The session is per-request scoped; Redis client is shared.
    """

    def __init__(
        self,
        redis:   aioredis.Redis,    # type: ignore[type-arg]
        session: AsyncSession,
    ) -> None:
        self._redis   = redis
        self._session = session

    # ── Public interface ───────────────────────────────────────

    async def get(self, cve_id: str) -> CVE | None:
        """
        Read-through: Redis → Postgres → None.
        Does NOT call NVD — that is the ingestion service's job.
        """
        cve_id = cve_id.upper()

        # Layer 1: Redis
        cached = await self._redis_get(cve_id)
        if cached is not None:
            return cached

        # Layer 2: Postgres
        pg_record = await self._pg_get(cve_id)
        if pg_record is not None:
            # Backfill Redis
            await self._redis_set(cve_id, pg_record)
            return pg_record

        return None

    async def get_many(self, cve_ids: list[str]) -> dict[str, CVE]:
        """Batch get — minimises round-trips."""
        cve_ids = [c.upper() for c in cve_ids]
        result: dict[str, CVE] = {}
        missing: list[str]     = []

        # Batch Redis lookup
        if cve_ids:
            raw_values = await self._redis.mget(*[self._redis_key(c) for c in cve_ids])
            for cve_id, raw in zip(cve_ids, raw_values):
                if raw:
                    try:
                        cve = self._deserialise(json.loads(raw))
                        result[cve_id] = cve
                    except Exception:
                        missing.append(cve_id)
                else:
                    missing.append(cve_id)

        # Batch Postgres lookup for misses
        if missing:
            pg_records = await self._pg_get_many(missing)
            for cve_id, cve in pg_records.items():
                result[cve_id] = cve
                await self._redis_set(cve_id, cve)

        return result

    async def set(self, cve: CVE) -> None:
        """Write to both layers."""
        await self._pg_upsert(cve)
        await self._redis_set(cve.cve_id, cve)

    async def is_stale(self, cve_id: str) -> bool:
        """True when the cached record is older than _PG_STALE_HOURS."""
        from app.infrastructure.database.models import CVECacheModel
        stmt = select(CVECacheModel.synced_at).where(
            CVECacheModel.cve_id == cve_id.upper()
        )
        synced_at = (await self._session.execute(stmt)).scalar_one_or_none()
        if synced_at is None:
            return True
        age = datetime.now(UTC) - synced_at
        return age > timedelta(hours=_PG_STALE_HOURS)

    async def invalidate(self, cve_id: str) -> None:
        """Remove from Redis (Postgres record stays, marked stale)."""
        await self._redis.delete(self._redis_key(cve_id.upper()))

    async def search_cached(
        self,
        keyword: str,
        limit: int = 50,
    ) -> list[CVE]:
        """
        Full-text search against the local Postgres CVE cache.
        Falls back to empty list if no results (caller then hits NVD).
        """
        from app.infrastructure.database.models import CVECacheModel

        stmt = (
            select(CVECacheModel)
            .where(
                CVECacheModel.description.ilike(f"%{keyword}%")
                | CVECacheModel.cve_id.ilike(f"%{keyword}%")
            )
            .order_by(CVECacheModel.cvss_v3_score.desc().nullslast())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._model_to_domain(row) for row in rows]

    # ── Redis helpers ──────────────────────────────────────────

    @staticmethod
    def _redis_key(cve_id: str) -> str:
        return f"cve:{cve_id}"

    async def _redis_get(self, cve_id: str) -> CVE | None:
        raw = await self._redis.get(self._redis_key(cve_id))
        if raw is None:
            return None
        try:
            return self._deserialise(json.loads(raw))
        except Exception as exc:
            logger.warning("redis_cve_deserialise_error", cve_id=cve_id, error=str(exc))
            return None

    async def _redis_set(self, cve_id: str, cve: CVE) -> None:
        try:
            serialised = json.dumps(self._serialise(cve))
            await self._redis.setex(
                self._redis_key(cve_id),
                _REDIS_TTL_SECONDS,
                serialised,
            )
        except Exception as exc:
            logger.warning("redis_cve_set_error", cve_id=cve_id, error=str(exc))

    # ── Postgres helpers ───────────────────────────────────────

    async def _pg_get(self, cve_id: str) -> CVE | None:
        from app.infrastructure.database.models import CVECacheModel
        stmt = select(CVECacheModel).where(CVECacheModel.cve_id == cve_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._model_to_domain(row) if row else None

    async def _pg_get_many(self, cve_ids: list[str]) -> dict[str, CVE]:
        from app.infrastructure.database.models import CVECacheModel
        stmt = select(CVECacheModel).where(CVECacheModel.cve_id.in_(cve_ids))
        rows = (await self._session.execute(stmt)).scalars().all()
        return {row.cve_id: self._model_to_domain(row) for row in rows}

    async def _pg_upsert(self, cve: CVE) -> None:
        import uuid

        from sqlalchemy.dialects.postgresql import insert

        from app.infrastructure.database.models import CVECacheModel

        data = self._domain_to_model_dict(cve)
        stmt = (
            insert(CVECacheModel)
            .values(id=str(uuid.uuid4()), **data, synced_at=datetime.now(UTC))
            .on_conflict_do_update(
                index_elements=["cve_id"],
                set_={k: v for k, v in data.items() if k != "cve_id"}
                | {"synced_at": datetime.now(UTC)},
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()

    # ── Serialisation ──────────────────────────────────────────

    def _serialise(self, cve: CVE) -> dict[str, Any]:
        """Convert CVE domain object to JSON-serialisable dict."""
        def _cvss(m: CVSSMetrics | None) -> dict | None:
            if m is None:
                return None
            return {
                "version":            m.version,
                "base_score":         m.base_score,
                "vector_string":      m.vector_string,
                "attack_vector":      m.attack_vector,
                "attack_complexity":  m.attack_complexity,
                "privileges_required":m.privileges_required,
                "user_interaction":   m.user_interaction,
                "scope":              m.scope,
                "confidentiality":    m.confidentiality,
                "integrity":          m.integrity,
                "availability":       m.availability,
            }

        return {
            "cve_id":      cve.cve_id,
            "description": cve.description,
            "published_at":cve.published_at.isoformat() if cve.published_at else None,
            "modified_at": cve.modified_at.isoformat()  if cve.modified_at  else None,
            "cvss_v3":     _cvss(cve.cvss_v3),
            "cvss_v2":     _cvss(cve.cvss_v2),
            "cwe_ids":     list(cve.cwe_ids),
            "references":  [
                {"url": r.url, "tags": list(r.tags)} for r in cve.references
            ],
            "cpe_matches": list(cve.cpe_matches),
        }

    def _deserialise(self, data: dict[str, Any]) -> CVE:
        """Reconstruct CVE domain object from JSON dict."""
        def _cvss(d: dict | None) -> CVSSMetrics | None:
            if d is None:
                return None
            return CVSSMetrics(
                version=            d.get("version", ""),
                base_score=         float(d.get("base_score", 0)),
                vector_string=      d.get("vector_string", ""),
                attack_vector=      d.get("attack_vector"),
                attack_complexity=  d.get("attack_complexity"),
                privileges_required=d.get("privileges_required"),
                user_interaction=   d.get("user_interaction"),
                scope=              d.get("scope"),
                confidentiality=    d.get("confidentiality"),
                integrity=          d.get("integrity"),
                availability=       d.get("availability"),
            )

        def _parse_dt(s: str | None) -> datetime | None:
            if not s:
                return None
            try:
                return datetime.fromisoformat(s)
            except ValueError:
                return None

        return CVE(
            cve_id=      data["cve_id"],
            description= data.get("description", ""),
            published_at=_parse_dt(data.get("published_at")),
            modified_at= _parse_dt(data.get("modified_at")),
            cvss_v3=     _cvss(data.get("cvss_v3")),
            cvss_v2=     _cvss(data.get("cvss_v2")),
            cwe_ids=     tuple(data.get("cwe_ids", [])),
            references=  tuple(
                CVEReference(url=r["url"], tags=tuple(r.get("tags", [])))
                for r in data.get("references", [])
            ),
            cpe_matches= tuple(data.get("cpe_matches", [])),
        )

    def _model_to_domain(self, row: Any) -> CVE:
        """Convert SQLAlchemy ORM row to CVE domain object."""
        refs_raw = row.references if isinstance(row.references, list) else []
        refs = tuple(
            CVEReference(
                url=r.get("url", ""),
                tags=tuple(r.get("tags", [])),
            )
            for r in refs_raw
        )

        cvss_v3: CVSSMetrics | None = None
        if row.cvss_v3_score is not None:
            cvss_v3 = CVSSMetrics(
                version="3.x",
                base_score=float(row.cvss_v3_score),
                vector_string=row.cvss_v3_vector or "",
            )

        return CVE(
            cve_id=      row.cve_id,
            description= row.description,
            published_at=row.published_at,
            modified_at= None,
            cvss_v3=     cvss_v3,
            cvss_v2=     None,
            cwe_ids=     tuple(row.cwe_ids or []),
            references=  refs,
            cpe_matches= tuple(
                cpe for cpe in (row.affected_products or {}).get("cpe_matches", [])
                if isinstance(cpe, str)
            ),
        )

    def _domain_to_model_dict(self, cve: CVE) -> dict[str, Any]:
        """Convert CVE domain object to dict for Postgres upsert."""
        return {
            "cve_id":       cve.cve_id,
            "description":  cve.description,
            "cvss_v3_score":cve.cvss_v3.base_score if cve.cvss_v3 else None,
            "cvss_v3_vector":cve.cvss_v3.vector_string if cve.cvss_v3 else None,
            "severity":     cve.severity.value,
            "affected_products": {
                "cpe_matches": list(cve.cpe_matches)
            },
            "references":   [
                {"url": r.url, "tags": list(r.tags)} for r in cve.references
            ],
            "cwe_ids":      list(cve.cwe_ids),
            "published_at": cve.published_at,
        }
