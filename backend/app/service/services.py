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
from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.blacklist import redis_client
from app.database.models import User
from app.worker.models import WorkerProfile
from app.service import models, schemas
from app.worker.schemas import PublicWorkerRead
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

    async def _invalidate_service_caches(
        self, service_id: UUID, owner_id: UUID | None = None
    ) -> None:
        """Invalidate service detail, search, and owner's service list cache."""
        if not self.cache:
            return

        keys_to_delete = [_cache_key("service:detail", service_id)]
        patterns_to_invalidate = [f"{CACHE_PREFIX}service:search:*"]

        if owner_id:
            patterns_to_invalidate.append(f"{CACHE_PREFIX}service:my_services:{owner_id}:*")
            patterns_to_invalidate.append(f"{CACHE_PREFIX}public_worker_profile:{owner_id}")

        logger.info(
            f"[CACHE ASYNC SERVICE] Invalidating service caches for service={service_id}, owner={owner_id}"
        )
        logger.debug(f"[CACHE ASYNC SERVICE] Keys to delete: {keys_to_delete}")
        logger.debug(f"[CACHE ASYNC SERVICE] Patterns to invalidate: {patterns_to_invalidate}")

        try:
            if keys_to_delete:
                await self.cache.delete(*keys_to_delete)
            for pattern in patterns_to_invalidate:
                await _invalidate_pattern(self.cache, pattern)
        except Exception as e:
            logger.error(f"[CACHE ASYNC SERVICE ERROR] Failed deleting service keys/patterns: {e}")

    def _prepare_worker_details_for_schema(
        self, user_obj: User | None, profile_obj: WorkerProfile | None
    ) -> PublicWorkerRead | None:
        """Helper to construct PublicWorkerRead from User and WorkerProfile objects."""
        if not user_obj:
            return None

        return PublicWorkerRead(
            user_id=user_obj.id,
            first_name=user_obj.first_name,
            last_name=user_obj.last_name,
            location=user_obj.location,
            is_available=profile_obj.is_available if profile_obj else False,
            is_kyc_verified=profile_obj.is_kyc_verified if profile_obj else False,
            professional_skills=profile_obj.professional_skills if profile_obj else None,
            work_experience=profile_obj.work_experience if profile_obj else None,
            years_experience=profile_obj.years_experience if profile_obj else None,
            bio=profile_obj.bio if profile_obj else None,
        )

    async def _construct_service_read_response(
        self, service_db_obj: models.Service
    ) -> schemas.ServiceRead:
        """Helper to construct the ServiceRead schema from a Service DB object."""
        worker_details_for_schema = self._prepare_worker_details_for_schema(
            service_db_obj.worker,
            service_db_obj.worker.worker_profile if service_db_obj.worker else None,
        )
        # Ensure all fields expected by ServiceRead are present
        return schemas.ServiceRead(
            id=service_db_obj.id,
            worker_id=service_db_obj.worker_id,
            title=service_db_obj.title,
            description=service_db_obj.description,
            location=service_db_obj.location,
            created_at=service_db_obj.created_at,
            updated_at=service_db_obj.updated_at,
            worker=worker_details_for_schema,
        )

    async def create_service(
        self, worker_id: UUID, data: schemas.ServiceCreate
    ) -> schemas.ServiceRead:
        """Create a new service for a worker."""
        await self._invalidate_service_caches(UUID(int=0), worker_id)
        logger.info(f"[SERVICE] Creating new service for worker {worker_id}")
        service_db_obj = models.Service(worker_id=worker_id, **data.model_dump())
        self.db.add(service_db_obj)
        try:
            await self.db.commit()
            await self.db.refresh(service_db_obj, attribute_names=['worker'])
            if service_db_obj.worker:
                await self.db.refresh(service_db_obj.worker, attribute_names=['worker_profile'])
            return await self._construct_service_read_response(service_db_obj)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"[SERVICE ERROR] Failed to create service: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to create service.")

    async def update_service(
        self, worker_id: UUID, service_id: UUID, data: schemas.ServiceUpdate
    ) -> schemas.ServiceRead:
        """Update an existing service listing (must belong to worker)."""
        stmt = (
            select(models.Service)
            .options(selectinload(models.Service.worker).selectinload(User.worker_profile))
            .filter_by(id=service_id, worker_id=worker_id)
        )
        service_db_obj = (await self.db.execute(stmt)).scalars().first()

        if not service_db_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Service not found or unauthorized."
            )

        await self._invalidate_service_caches(service_id, worker_id)
        logger.info(f"Updating service {service_id} for worker {worker_id}")

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return await self._construct_service_read_response(service_db_obj)

        for field, val in update_data.items():
            if hasattr(service_db_obj, field):
                setattr(service_db_obj, field, val)
        try:
            await self.db.commit()
            await self.db.refresh(service_db_obj, attribute_names=['worker'])
            if service_db_obj.worker:
                await self.db.refresh(service_db_obj.worker, attribute_names=['worker_profile'])

            response = await self._construct_service_read_response(service_db_obj)

            if self.cache:
                key = _cache_key("service:detail", service_id)
                try:
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
        stmt = select(models.Service).filter_by(id=service_id, worker_id=worker_id)
        service_db_obj = (await self.db.execute(stmt)).scalars().first()
        if not service_db_obj:
            raise HTTPException(status_code=404, detail="Service not found or unauthorized.")

        await self._invalidate_service_caches(service_id, worker_id)
        logger.info(f"[SERVICE] Deleting service {service_id} for worker {worker_id}")
        try:
            await self.db.delete(service_db_obj)
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"[SERVICE ERROR] Failed to delete service: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to delete service.")

    async def get_my_services(
        self, worker_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[schemas.ServiceRead], int]:
        key = _paginated_cache_key("service:my_services", worker_id, skip, limit)
        if self.cache:
            data = await self.cache.get(key)
            if data:
                try:
                    payload = json.loads(data)
                    items = [schemas.ServiceRead.model_validate(i) for i in payload["items"]]
                    return items, payload["total_count"]
                except Exception as e:
                    logger.error(
                        f"Cache data for my_services {key} failed validation: {e}. Fetching from DB."
                    )

        count = (
            await self.db.execute(
                select(func.count(models.Service.id)).filter(models.Service.worker_id == worker_id)
            )
        ).scalar_one()

        stmt = (
            select(models.Service)
            .options(selectinload(models.Service.worker).selectinload(User.worker_profile))
            .filter_by(worker_id=worker_id)
            .order_by(models.Service.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        service_db_objs = (await self.db.execute(stmt)).unique().scalars().all()

        items = [await self._construct_service_read_response(s) for s in service_db_objs]

        if self.cache:
            await self.cache.set(
                key,
                json.dumps(
                    {"items": [i.model_dump(mode='json') for i in items], "total_count": count}
                ),
                ex=DEFAULT_CACHE_TTL,
            )
        return items, count

    async def get_public_service_detail(self, service_id: UUID) -> schemas.ServiceRead:
        key = _cache_key("service:detail", service_id)
        if self.cache:
            data = await self.cache.get(key)
            if data:
                try:
                    return schemas.ServiceRead.model_validate_json(data)
                except Exception as e:
                    logger.error(
                        f"Cache data for service:detail:{service_id} failed validation: {e}. Fetching from DB."
                    )

        stmt = (
            select(models.Service)
            .options(selectinload(models.Service.worker).selectinload(User.worker_profile))
            .filter_by(id=service_id)
        )
        service_db_obj = (await self.db.execute(stmt)).scalars().first()

        if not service_db_obj:
            raise HTTPException(status_code=404, detail="Service not found.")

        response = await self._construct_service_read_response(service_db_obj)

        if self.cache:
            await self.cache.set(key, response.model_dump_json(), ex=DEFAULT_CACHE_TTL)
        return response

    async def search_services(
        self,
        title: str | None = None,
        location: str | None = None,
        name: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[schemas.ServiceRead], int]:
        title_norm = title.lower().strip() if title else ""
        loc_norm = location.lower().strip() if location else ""
        name_norm = name.lower().strip() if name else ""

        params = f"title={title_norm}:location={loc_norm}:name={name_norm}"
        hash_key = hashlib.sha1(params.encode()).hexdigest()[:10]
        key = _paginated_cache_key(f"service:search:{hash_key}", "results", skip, limit)

        if self.cache:
            data = await self.cache.get(key)
            if data:
                try:
                    payload = json.loads(data)
                    items = [schemas.ServiceRead.model_validate(i) for i in payload["items"]]
                    return items, payload["total_count"]
                except Exception as e:
                    logger.error(
                        f"Cache data for search {key} failed validation: {e}. Fetching from DB."
                    )

        query = select(models.Service).options(
            selectinload(models.Service.worker).selectinload(User.worker_profile)
        )

        filters: list[ColumnElement[bool]] = []
        if title_norm:
            filters.append(models.Service.title.ilike(f"%{title_norm}%"))
        if loc_norm:
            filters.append(models.Service.location.ilike(f"%{loc_norm}%"))

        if name_norm:
            query = query.join(User, models.Service.worker_id == User.id)
            name_parts = name_norm.split()
            if len(name_parts) > 1:
                filters.append(
                    or_(
                        User.first_name.ilike(f"%{name_parts[0]}%"),
                        User.last_name.ilike(f"%{name_parts[-1]}%"),
                        func.concat(User.first_name, " ", User.last_name).ilike(f"%{name_norm}%"),
                    )
                )
            else:
                filters.append(
                    or_(
                        User.first_name.ilike(f"%{name_norm}%"),
                        User.last_name.ilike(f"%{name_norm}%"),
                    )
                )

        if filters:
            query = query.filter(*filters)

        count_query = select(func.count()).select_from(
            query.with_only_columns(models.Service.id).subquery()
        )
        total_count = (await self.db.execute(count_query)).scalar_one()

        paginated_query = query.order_by(models.Service.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(paginated_query)
        service_db_objs = result.unique().scalars().all()

        items = [await self._construct_service_read_response(s) for s in service_db_objs]

        if self.cache:
            to_cache = {
                "items": [i.model_dump(mode="json") for i in items],
                "total_count": total_count,
            }
            await self.cache.set(key, json.dumps(to_cache), ex=DEFAULT_CACHE_TTL)

        return items, total_count
