"""
backend/app/service/services.py

Service Listing Service Layer
Manages CRUD operations and search for service listings created by workers.
Implements Redis caching for efficiency and invalidates relevant cache entries
on write operations.
"""

import hashlib
import json
import logging
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.blacklist import redis_client
from app.service import models, schemas
from app.worker.services import _cache_key, _paginated_cache_key, DEFAULT_CACHE_TTL, CACHE_PREFIX

logger = logging.getLogger(__name__)


# ---------------------------------------------------
# Utility: Pattern-based Cache Invalidation
# ---------------------------------------------------
async def _invalidate_pattern(cache: Any, pattern: str) -> None:
    """Delete all Redis keys matching a given pattern."""
    if not cache:
        return
    async for key in cache.scan_iter(match=pattern):
        await cache.delete(key)


# ---------------------------------------------------
# ServiceListingService
# ---------------------------------------------------
class ServiceListingService:
    """Handles service creation, update, deletion, listing, and public search."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.cache = redis_client
        if not self.cache:
            logger.warning("[CACHE] Redis client not configured, caching disabled.")

    async def _invalidate_service_caches(self, service_id: UUID, owner_id: UUID) -> None:
        """Invalidate service detail, search, and owner's service list cache."""
        if not self.cache:
            return
        await self.cache.delete(_cache_key("service:detail", service_id))
        await _invalidate_pattern(self.cache, f"{CACHE_PREFIX}service:search:*")
        await _invalidate_pattern(self.cache, f"{CACHE_PREFIX}service:my_services:{owner_id}:*")

    async def create_service(
        self, worker_id: UUID, data: schemas.ServiceCreate
    ) -> schemas.ServiceRead:
        """Create a new service for a worker."""
        await self._invalidate_service_caches(UUID(int=0), worker_id)
        logger.info(f"[SERVICE] Creating new service for worker {worker_id}")
        service = models.Service(worker_id=worker_id, **data.model_dump())
        self.db.add(service)
        try:
            await self.db.commit()
            await self.db.refresh(service)
            return schemas.ServiceRead.model_validate(service)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"[SERVICE ERROR] Failed to create service: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to create service.")

    async def update_service(
        self, worker_id: UUID, service_id: UUID, data: schemas.ServiceUpdate
    ) -> schemas.ServiceRead:
        """Update an existing service listing (must belong to worker)."""
        await self._invalidate_service_caches(service_id, worker_id)
        logger.info(f"Updating service {service_id} for worker {worker_id}")
        stmt = select(models.Service).filter_by(id=service_id, worker_id=worker_id)
        service = (await self.db.execute(stmt)).scalars().first()
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Service not found or unauthorized."
            )
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return schemas.ServiceRead.model_validate(service)

        for field, val in update_data.items():
            if hasattr(service, field):
                setattr(service, field, val)
        try:
            await self.db.commit()
            await self.db.refresh(service)
            response = schemas.ServiceRead.model_validate(service)
            if self.cache:
                key = _cache_key("service:detail", service_id)
                try:
                    # Ensure self.cache is checked before calling set
                    await self.cache.set(key, response.model_dump_json(), ex=DEFAULT_CACHE_TTL)
                except Exception as e:
                    logger.error(
                        f"[CACHE ASYNC WRITE ERROR] Post-update cache set failed for {key}: {e}"
                    )
            return response
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update service: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update service.",
            )

    async def delete_service(self, worker_id: UUID, service_id: UUID) -> None:
        """Delete a service listing."""
        await self._invalidate_service_caches(service_id, worker_id)
        logger.info(f"[SERVICE] Deleting service {service_id} for worker {worker_id}")
        stmt = select(models.Service).filter_by(id=service_id, worker_id=worker_id)
        service = (await self.db.execute(stmt)).scalars().first()
        if not service:
            raise HTTPException(status_code=404, detail="Service not found or unauthorized.")
        try:
            await self.db.delete(service)
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"[SERVICE ERROR] Failed to delete service: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to delete service.")

    async def get_my_services(
        self, worker_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[schemas.ServiceRead], int]:
        """Retrieve services listed by a specific worker."""
        key = _paginated_cache_key("service:my_services", worker_id, skip, limit)
        if self.cache:
            data = await self.cache.get(key)
            if data:
                payload = json.loads(data)
                items = [schemas.ServiceRead.model_validate(i) for i in payload["items"]]
                return items, payload["total_count"]
        count = (
            await self.db.execute(
                select(func.count(models.Service.id)).filter(models.Service.worker_id == worker_id)
            )
        ).scalar_one()
        rows = (
            (
                await self.db.execute(
                    select(models.Service)
                    .filter_by(worker_id=worker_id)
                    .order_by(models.Service.created_at.desc())
                    .offset(skip)
                    .limit(limit)
                )
            )
            .unique()
            .scalars()
            .all()
        )
        items = [schemas.ServiceRead.model_validate(r) for r in rows]
        if self.cache:
            await self.cache.set(
                key,
                json.dumps({"items": [i.model_dump() for i in items], "total_count": count}),
                ex=DEFAULT_CACHE_TTL,
            )
        return items, count

    async def get_public_service_detail(self, service_id: UUID) -> schemas.ServiceRead:
        """Get publicly visible details of a service."""
        key = _cache_key("service:detail", service_id)
        if self.cache:
            data = await self.cache.get(key)
            if data:
                return schemas.ServiceRead.model_validate_json(data)
        stmt = select(models.Service).filter_by(id=service_id)
        service = (await self.db.execute(stmt)).scalars().first()
        if not service:
            raise HTTPException(status_code=404, detail="Service not found.")
        response = schemas.ServiceRead.model_validate(service)
        if self.cache:
            await self.cache.set(key, response.model_dump_json(), ex=DEFAULT_CACHE_TTL)
        return response

    async def search_services(
        self, title: str | None = None, location: str | None = None, skip: int = 0, limit: int = 100
    ) -> tuple[list[schemas.ServiceRead], int]:
        """Search for services by title and/or location."""
        title_norm = title.lower().strip() if title else ""
        loc_norm = location.lower().strip() if location else ""
        params = f"title={title_norm}:location={loc_norm}"
        hash_key = hashlib.sha1(params.encode()).hexdigest()[:10]
        key = _paginated_cache_key(f"service:search:{hash_key}", "results", skip, limit)

        if self.cache:
            data = await self.cache.get(key)
            if data:
                payload = json.loads(data)
                items = [schemas.ServiceRead.model_validate(i) for i in payload["items"]]
                return items, payload["total_count"]

        query = select(models.Service)
        if title:
            query = query.filter(models.Service.title.ilike(f"%{title}%"))
        if location:
            query = query.filter(models.Service.location.ilike(f"%{location}%"))

        subq = query.with_only_columns(func.count()).subquery()
        count = (await self.db.execute(select(func.count()).select_from(subq))).scalar_one()
        rows = (
            (
                await self.db.execute(
                    query.order_by(models.Service.created_at.desc()).offset(skip).limit(limit)
                )
            )
            .unique()
            .scalars()
            .all()
        )
        items = [schemas.ServiceRead.model_validate(r) for r in rows]

        if self.cache:
            await self.cache.set(
                key,
                json.dumps({"items": [i.model_dump() for i in items], "total_count": count}),
                ex=DEFAULT_CACHE_TTL,
            )
        return items, count
