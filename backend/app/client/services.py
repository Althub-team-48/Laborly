"""
backend/app/client/services.py

Client Service Layer (Corrected Cache Invalidation)
Handles client profile operations, job management, favorites handling,
and profile picture utilities. Leverages Redis for caching where available.
"""

import json
import logging
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.client import models, schemas
from app.client.schemas import (
    ClientJobRead,
    FavoriteRead,
    FavoriteWorkerInfo,
    ClientJobWorkerInfo,
    ClientJobServiceInfo,
)
from app.core.blacklist import redis_client
from app.core.schemas import MessageResponse
from app.core.upload import generate_presigned_url, get_s3_key_from_url
from app.database.enums import UserRole
from app.database.models import User
from app.job.models import Job
from app.service.models import Service as ServiceModel

from app.worker.services import (
    _cache_key,
    _paginated_cache_key,
    DEFAULT_CACHE_TTL,
    CACHE_PREFIX,
)

logger = logging.getLogger(__name__)

# -------------------------------
# --- Client Cache Namespaces ---
# -------------------------------
CLIENT_PROFILE_NS = "client_profile"
PUBLIC_CLIENT_PROFILE_NS = "public_client_profile"
CLIENT_FAVORITES_NS = "client_favorites"
CLIENT_JOBS_NS = "client_jobs"


# -------------------------
# --- Utility Functions ---
# -------------------------
def _merge_client_profile_data(user: User, profile: models.ClientProfile) -> dict[str, Any]:
    """Combine user and profile data into a single dictionary for ClientProfileRead."""
    data = {k: v for k, v in vars(profile).items() if not k.startswith('_')}
    data.update(
        {
            'user_id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone_number': user.phone_number,
            'location': user.location,
        }
    )
    return data


# -----------------------------------------
# --- Cache Invalidation Pattern Helper ---
# -----------------------------------------
async def _invalidate_pattern(cache: Any, pattern: str) -> None:
    """Delete keys matching a given pattern using the full key structure."""
    if not cache:
        return
    logger.debug(f"[CACHE ASYNC CLIENT] Scanning pattern: {pattern}")
    keys_deleted_count = 0
    try:
        if not redis_client:
            logger.warning(
                "[CACHE ASYNC CLIENT] Redis client not available for pattern invalidation."
            )
            return
        async for key in redis_client.scan_iter(match=pattern):
            await redis_client.delete(key)
            keys_deleted_count += 1
        logger.info(
            f"[CACHE ASYNC CLIENT] Deleted {keys_deleted_count} keys matching pattern {pattern}"
        )
    except Exception as e:
        logger.error(f"[CACHE ASYNC CLIENT ERROR] Failed pattern deletion for {pattern}: {e}")


class ClientService:
    """Service class for client operations with caching and database support."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.cache = redis_client
        if not self.cache:
            logger.warning("[CACHE ASYNC CLIENT] Redis client not configured, caching disabled.")

    async def _invalidate_profile_caches(self, user_id: UUID) -> None:
        """Remove user-related cache entries for client profile."""
        if not self.cache:
            return
        keys = [
            _cache_key(CLIENT_PROFILE_NS, user_id),
            _cache_key(PUBLIC_CLIENT_PROFILE_NS, user_id),
        ]
        logger.info(f"[CACHE ASYNC CLIENT] Invalidating profile caches for client {user_id}")
        try:
            if keys:
                await self.cache.delete(*keys)
        except Exception as e:
            logger.error(
                f"[CACHE ASYNC CLIENT ERROR] Failed deleting profile keys for {user_id}: {e}"
            )

    async def _invalidate_paginated_cache(self, namespace: str, user_id: UUID) -> None:
        """Invalidate paginated cache entries based on namespace and user ID."""
        if not self.cache:
            return
        pattern = f"{CACHE_PREFIX}{namespace}:{user_id}:*"
        await _invalidate_pattern(self.cache, pattern)

    async def _get_user(self, user_id: UUID, role: UserRole) -> User:
        """Fetch a user and validate role. Eager load profiles for potential use."""
        user = await self.db.get(
            User,
            user_id,
            options=[selectinload(User.client_profile), selectinload(User.worker_profile)],
        )
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if user.role != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action requires {role.name.lower()} role.",
            )
        return user

    async def _get_user_and_client_profile(
        self, user_id: UUID, role: UserRole = UserRole.CLIENT
    ) -> tuple[User, models.ClientProfile]:
        """Fetch both User and associated ClientProfile, create profile if missing."""
        user = await self._get_user(user_id, role)
        profile: models.ClientProfile | None
        if user.client_profile:
            profile = user.client_profile
        else:
            result = await self.db.execute(select(models.ClientProfile).filter_by(user_id=user_id))
            profile = result.scalars().unique().one_or_none()

        if not profile:
            profile = models.ClientProfile(user_id=user_id)
            self.db.add(profile)
            await self.db.flush()
            await self.db.refresh(profile)
            user.client_profile = profile
            logger.info(f"[CLIENT] Created client profile for {user_id}")
        return user, profile

    def _construct_favorite_worker_info(self, worker_user: User) -> FavoriteWorkerInfo:
        """Helper to construct FavoriteWorkerInfo from a User model (worker)."""
        worker_profile = worker_user.worker_profile
        return FavoriteWorkerInfo(
            id=worker_user.id,
            first_name=worker_user.first_name,
            last_name=worker_user.last_name,
            professional_skills=worker_profile.professional_skills if worker_profile else None,
            location=worker_user.location,
            is_available=worker_profile.is_available if worker_profile else False,
        )

    def _construct_client_job_worker_info(
        self, worker_user: User | None
    ) -> ClientJobWorkerInfo | None:
        if not worker_user:
            return None
        return ClientJobWorkerInfo.model_validate(worker_user)

    def _construct_client_job_service_info(
        self, service_model: ServiceModel | None
    ) -> ClientJobServiceInfo | None:
        if not service_model:
            return None
        return ClientJobServiceInfo.model_validate(service_model)

    def _construct_favorite_read(self, fav_model: models.FavoriteWorker) -> FavoriteRead:
        if not fav_model.worker:
            raise ValueError("FavoriteWorker model is missing related worker user.")
        worker_info = self._construct_favorite_worker_info(fav_model.worker)

        return FavoriteRead(
            id=fav_model.id,
            client_id=fav_model.client_id,
            worker=worker_info,
            created_at=fav_model.created_at,
        )

    def _construct_client_job_read(self, job_model: Job) -> ClientJobRead:
        worker_info = self._construct_client_job_worker_info(job_model.worker)
        service_info = self._construct_client_job_service_info(job_model.service)

        return ClientJobRead(
            id=job_model.id,
            service=service_info,
            worker=worker_info,
            status=job_model.status,
            started_at=job_model.started_at,
            completed_at=job_model.completed_at,
            cancelled_at=job_model.cancelled_at,
            cancel_reason=job_model.cancel_reason,
            created_at=job_model.created_at,
            updated_at=job_model.updated_at,
        )

    # ---------------------------------------------------
    # Profile Picture Utilities
    # ---------------------------------------------------
    async def get_profile_picture_presigned_url(self, user_id: UUID) -> str | None:
        user = await self._get_user(user_id, UserRole.CLIENT)
        if not user.profile_picture:
            return None
        key = get_s3_key_from_url(user.profile_picture)
        if not key:
            return None
        return generate_presigned_url(key, expiration=3600)

    # ---------------------------------------------------
    # Client Profile (Authenticated)
    # ---------------------------------------------------
    async def get_profile(self, user_id: UUID) -> schemas.ClientProfileRead:
        cache_key = _cache_key(CLIENT_PROFILE_NS, user_id)
        if self.cache:
            try:
                data = await self.cache.get(cache_key)
                if data:
                    logger.info(f"[CACHE ASYNC HIT] Client profile for {user_id}")
                    return schemas.ClientProfileRead.model_validate_json(data)
            except Exception as e:
                logger.error(f"[CACHE ASYNC READ ERROR] Client profile {user_id}: {e}")

        logger.info(f"[CACHE ASYNC MISS] Fetching client profile from DB for {user_id}")
        user, profile = await self._get_user_and_client_profile(user_id)
        merged_data = _merge_client_profile_data(user, profile)
        merged_data['id'] = profile.id
        merged_data['created_at'] = profile.created_at
        merged_data['updated_at'] = profile.updated_at

        response = schemas.ClientProfileRead.model_validate(merged_data)

        if self.cache:
            try:
                await self.cache.set(cache_key, response.model_dump_json(), ex=DEFAULT_CACHE_TTL)
                logger.info(f"[CACHE ASYNC SET] Client profile for {user_id}")
            except Exception as e:
                logger.error(f"[CACHE ASYNC WRITE ERROR] Client profile {user_id}: {e}")
        return response

    async def update_profile(
        self, user_id: UUID, payload: schemas.ClientProfileUpdate
    ) -> schemas.ClientProfileRead:
        await self._invalidate_profile_caches(user_id)
        user, profile = await self._get_user_and_client_profile(user_id)
        data = payload.model_dump(exclude_unset=True)
        user_updated, profile_updated = False, False

        user_fields = {'first_name', 'last_name', 'location', 'phone_number'}
        profile_fields = {'profile_description', 'address'}

        for field in user_fields:
            if field in data:
                setattr(user, field, data[field])
                user_updated = True
        for field in profile_fields:
            if field in data:
                setattr(profile, field, data[field])
                profile_updated = True

        if not user_updated and not profile_updated:
            logger.info(f"No profile fields to update for client {user_id}")
        else:
            try:
                await self.db.commit()
                if user_updated:
                    await self.db.refresh(user)
                if profile_updated:
                    await self.db.refresh(profile)
            except Exception as e:
                await self.db.rollback()
                logger.error(f"Failed profile update for client {user_id}: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update profile",
                )
        return await self.get_profile(user_id)

    async def update_profile_picture(self, user_id: UUID, picture_url: str) -> MessageResponse:
        await self._invalidate_profile_caches(user_id)
        user, _ = await self._get_user_and_client_profile(user_id)
        if user.profile_picture != picture_url:
            user.profile_picture = picture_url
            try:
                await self.db.commit()
                await self.db.refresh(user)
            except Exception as e:
                await self.db.rollback()
                logger.error(
                    f"Failed profile picture update for client {user_id}: {e}", exc_info=True
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update picture",
                )
        await self.get_profile(user_id)
        return MessageResponse(detail="Profile picture updated successfully.")

    # ---------------------------------------------------
    # Public Client Profile
    # ---------------------------------------------------
    async def get_public_client_profile(self, user_id: UUID) -> schemas.PublicClientRead:
        cache_key = _cache_key(PUBLIC_CLIENT_PROFILE_NS, user_id)
        if self.cache:
            try:
                data = await self.cache.get(cache_key)
                if data:
                    logger.info(f"[CACHE ASYNC HIT] Public client profile for {user_id}")
                    return schemas.PublicClientRead.model_validate_json(data)
            except Exception as e:
                logger.error(f"[CACHE ASYNC READ ERROR] Public client profile {user_id}: {e}")

        logger.info(f"[CACHE ASYNC MISS] Fetching public client profile from DB for {user_id}")
        user = await self.db.get(User, user_id)
        if not user or user.role != UserRole.CLIENT:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

        response = schemas.PublicClientRead.model_validate(user)

        if self.cache:
            try:
                await self.cache.set(cache_key, response.model_dump_json(), ex=DEFAULT_CACHE_TTL)
                logger.info(f"[CACHE ASYNC SET] Public client profile for {user_id}")
            except Exception as e:
                logger.error(f"[CACHE ASYNC WRITE ERROR] Public client profile {user_id}: {e}")
        return response

    # ---------------------------------------------------
    # Favorites (Authenticated)
    # ---------------------------------------------------
    async def list_favorites(
        self, client_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[FavoriteRead], int]:
        cache_key = _paginated_cache_key(CLIENT_FAVORITES_NS, client_id, skip, limit)
        if self.cache:
            try:
                data = await self.cache.get(cache_key)
                if data:
                    logger.info(
                        f"[CACHE ASYNC HIT] Client favorites list for {client_id} (skip={skip}, limit={limit})"
                    )
                    payload = json.loads(data)
                    items = [FavoriteRead.model_validate(i) for i in payload['items']]
                    return items, payload['total_count']
            except Exception as e:
                logger.error(f"[CACHE ASYNC READ ERROR] Client favorites list {client_id}: {e}")

        logger.info(f"[CACHE ASYNC MISS] Fetching client favorites list from DB for {client_id}")
        await self._get_user(client_id, UserRole.CLIENT)

        total_stmt = select(func.count(models.FavoriteWorker.id)).filter_by(client_id=client_id)
        total = (await self.db.execute(total_stmt)).scalar_one()

        fav_stmt = (
            select(models.FavoriteWorker)
            .options(
                selectinload(models.FavoriteWorker.worker).options(
                    selectinload(User.worker_profile)
                )
            )
            .filter_by(client_id=client_id)
            .order_by(models.FavoriteWorker.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        fav_db_models = (await self.db.execute(fav_stmt)).unique().scalars().all()
        favs_read = [self._construct_favorite_read(f) for f in fav_db_models]

        if self.cache:
            try:
                serializable_items = [f.model_dump(mode='json') for f in favs_read]
                payload_to_cache = json.dumps({'items': serializable_items, 'total_count': total})
                await self.cache.set(cache_key, payload_to_cache, ex=DEFAULT_CACHE_TTL)
                logger.info(
                    f"[CACHE ASYNC SET] Client favorites list for {client_id} (skip={skip}, limit={limit})"
                )
            except Exception as e:
                logger.error(f"[CACHE ASYNC WRITE ERROR] Client favorites list {client_id}: {e}")
        return favs_read, total

    async def add_favorite(self, client_id: UUID, worker_id: UUID) -> FavoriteRead:
        await self._invalidate_paginated_cache(CLIENT_FAVORITES_NS, client_id)
        await self._get_user(client_id, UserRole.CLIENT)
        await self._get_user(worker_id, UserRole.WORKER)

        exists_stmt = select(models.FavoriteWorker).filter_by(
            client_id=client_id, worker_id=worker_id
        )
        existing_fav = (await self.db.execute(exists_stmt)).scalar_one_or_none()
        if existing_fav:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already favorited")

        fav = models.FavoriteWorker(client_id=client_id, worker_id=worker_id)
        self.db.add(fav)
        try:
            await self.db.commit()
            await self.db.refresh(fav, attribute_names=["worker"])
            if fav.worker:
                await self.db.refresh(fav.worker, attribute_names=["worker_profile"])
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed add favorite for client {client_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to add favorite"
            )
        return self._construct_favorite_read(fav)

    async def remove_favorite(self, client_id: UUID, worker_id: UUID) -> None:
        await self._invalidate_paginated_cache(CLIENT_FAVORITES_NS, client_id)
        await self._get_user(client_id, UserRole.CLIENT)

        fav_stmt = select(models.FavoriteWorker).filter_by(client_id=client_id, worker_id=worker_id)
        fav = (await self.db.execute(fav_stmt)).scalar_one_or_none()
        if not fav:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favorite not found")
        try:
            await self.db.delete(fav)
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed remove favorite for client {client_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove favorite",
            )

    # ---------------------------------------------------
    # Job History (Authenticated)
    # ---------------------------------------------------
    async def get_jobs(
        self, client_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[ClientJobRead], int]:
        cache_key = _paginated_cache_key(CLIENT_JOBS_NS, client_id, skip, limit)
        if self.cache:
            try:
                data = await self.cache.get(cache_key)
                if data:
                    logger.info(
                        f"[CACHE ASYNC HIT] Client jobs list for {client_id} (skip={skip}, limit={limit})"
                    )
                    payload = json.loads(data)
                    items = [ClientJobRead.model_validate(i) for i in payload['items']]
                    return items, payload['total_count']
            except Exception as e:
                logger.error(f"[CACHE ASYNC READ ERROR] Client jobs list {client_id}: {e}")

        logger.info(f"[CACHE ASYNC MISS] Fetching client jobs list from DB for {client_id}")
        await self._get_user(client_id, UserRole.CLIENT)

        total_stmt = select(func.count(Job.id)).filter_by(client_id=client_id)
        total = (await self.db.execute(total_stmt)).scalar_one()

        job_stmt = (
            select(Job)
            .options(
                selectinload(Job.worker),
                selectinload(Job.service),
            )
            .filter_by(client_id=client_id)
            .order_by(Job.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        job_db_models = (await self.db.execute(job_stmt)).unique().scalars().all()
        jobs_read = [self._construct_client_job_read(j) for j in job_db_models]

        if self.cache:
            try:
                serializable_items = [j.model_dump(mode='json') for j in jobs_read]
                payload_to_cache = json.dumps({'items': serializable_items, 'total_count': total})
                await self.cache.set(cache_key, payload_to_cache, ex=DEFAULT_CACHE_TTL)
                logger.info(
                    f"[CACHE ASYNC SET] Client jobs list for {client_id} (skip={skip}, limit={limit})"
                )
            except Exception as e:
                logger.error(f"[CACHE ASYNC WRITE ERROR] Client jobs list {client_id}: {e}")
        return jobs_read, total

    async def get_job_detail(self, client_id: UUID, job_id: UUID) -> ClientJobRead:
        await self._get_user(client_id, UserRole.CLIENT)

        job_stmt = (
            select(Job)
            .options(selectinload(Job.worker), selectinload(Job.service))
            .filter_by(id=job_id, client_id=client_id)
        )
        job_db_model = (await self.db.execute(job_stmt)).unique().scalar_one_or_none()

        if not job_db_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Job not found or unauthorized"
            )
        return self._construct_client_job_read(job_db_model)

    async def invalidate_job_cache(self, client_id: UUID) -> None:
        """Explicitly clear job list cache for a client."""
        await self._invalidate_paginated_cache(CLIENT_JOBS_NS, client_id)
