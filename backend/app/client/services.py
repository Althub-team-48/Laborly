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

from app.client import models, schemas
from app.client.schemas import ClientJobRead, FavoriteRead
from app.core.blacklist import redis_client
from app.core.schemas import MessageResponse
from app.core.upload import generate_presigned_url, get_s3_key_from_url
from app.database.enums import UserRole
from app.database.models import User
from app.job.models import Job
from app.worker.services import _cache_key, _paginated_cache_key, DEFAULT_CACHE_TTL, CACHE_PREFIX

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
def _merge_client_profile(user: User, profile: models.ClientProfile) -> dict[str, Any]:
    """Combine user and profile data into a single dictionary."""
    data = {k: v for k, v in vars(profile).items() if not k.startswith('_')}
    data.update(
        {
            'user_id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'phone_number': user.phone_number,
            'location': user.location,
            'profile_picture': user.profile_picture,
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
        async for key in cache.scan_iter(match=pattern):
            await cache.delete(key)
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
        """Fetch a user and validate role."""
        user = await self.db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if user.role != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action requires {role.name.lower()} role.",
            )
        return user

    async def _get_user_and_profile(
        self, user_id: UUID, role: UserRole
    ) -> tuple[User, models.ClientProfile]:
        """Fetch both User and associated ClientProfile, create profile if missing."""
        user = await self._get_user(user_id, role)
        result = await self.db.execute(select(models.ClientProfile).filter_by(user_id=user_id))
        profile = result.scalars().unique().one_or_none()
        if not profile:
            profile = models.ClientProfile(user_id=user_id)
            self.db.add(profile)
            await self.db.flush()
            await self.db.refresh(profile)
            logger.info(f"[CLIENT] Created client profile for {user_id}")
        return user, profile

    # ---------------------------------------------------
    # Profile Picture Utilities
    # ---------------------------------------------------
    async def get_profile_picture_presigned_url(self, user_id: UUID) -> str | None:
        """Generate a presigned S3 URL for the user's profile picture."""
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
        """Retrieve the authenticated client's profile with cache support."""
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
        user, profile = await self._get_user_and_profile(user_id, UserRole.CLIENT)
        merged = _merge_client_profile(user, profile)
        response = schemas.ClientProfileRead.model_validate(merged)

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
        """Update the client’s profile and user details."""
        await self._invalidate_profile_caches(user_id)
        user, profile = await self._get_user_and_profile(user_id, UserRole.CLIENT)
        data = payload.model_dump(exclude_unset=True)
        user_updated, profile_updated = False, False
        for f in {'first_name', 'last_name', 'location', 'phone_number'} & data.keys():
            if hasattr(user, f):
                setattr(user, f, data[f])
            user_updated = True
        for f in {'profile_description', 'address'} & data.keys():
            if hasattr(profile, f):
                setattr(profile, f, data[f])
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
        """Update the client's profile picture."""
        await self._invalidate_profile_caches(user_id)
        user, _ = await self._get_user_and_profile(user_id, UserRole.CLIENT)
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
        """Return limited public information for a client."""
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
        data = {
            'user_id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'location': user.location,
            'profile_picture': user.profile_picture,
        }
        response = schemas.PublicClientRead.model_validate(data)
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
        """Retrieve list of a client's favorite workers with cache support."""
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
        total = (
            await self.db.execute(
                select(func.count(models.FavoriteWorker.id)).filter_by(client_id=client_id)
            )
        ).scalar_one()
        rows = await self.db.execute(
            select(models.FavoriteWorker)
            .filter_by(client_id=client_id)
            .order_by(models.FavoriteWorker.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        favs = [FavoriteRead.model_validate(f) for f in rows.scalars().all()]

        if self.cache:
            try:
                payload_to_cache = json.dumps(
                    {'items': [f.model_dump() for f in favs], 'total_count': total}
                )
                await self.cache.set(cache_key, payload_to_cache, ex=DEFAULT_CACHE_TTL)
                logger.info(
                    f"[CACHE ASYNC SET] Client favorites list for {client_id} (skip={skip}, limit={limit})"
                )
            except Exception as e:
                logger.error(f"[CACHE ASYNC WRITE ERROR] Client favorites list {client_id}: {e}")
        return favs, total

    async def add_favorite(self, client_id: UUID, worker_id: UUID) -> FavoriteRead:
        """Add a worker to a client's favorites."""
        await self._invalidate_paginated_cache(CLIENT_FAVORITES_NS, client_id)
        await self._get_user(client_id, UserRole.CLIENT)
        await self._get_user(worker_id, UserRole.WORKER)
        exists = await self.db.execute(
            select(models.FavoriteWorker).filter_by(client_id=client_id, worker_id=worker_id)
        )
        if exists.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already favorited")
        fav = models.FavoriteWorker(client_id=client_id, worker_id=worker_id)
        self.db.add(fav)
        try:
            await self.db.commit()
            await self.db.refresh(fav)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed add favorite for client {client_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to add favorite"
            )
        return FavoriteRead.model_validate(fav)

    async def remove_favorite(self, client_id: UUID, worker_id: UUID) -> None:
        """Remove a worker from a client’s favorites list."""
        await self._invalidate_paginated_cache(CLIENT_FAVORITES_NS, client_id)
        await self._get_user(client_id, UserRole.CLIENT)
        res = await self.db.execute(
            select(models.FavoriteWorker).filter_by(client_id=client_id, worker_id=worker_id)
        )
        fav = res.scalar_one_or_none()
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
        """Fetch jobs posted by the client."""
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
        total = (
            await self.db.execute(select(func.count(Job.id)).filter_by(client_id=client_id))
        ).scalar_one()
        rows = await self.db.execute(
            select(Job)
            .filter_by(client_id=client_id)
            .order_by(Job.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        jobs = [ClientJobRead.model_validate(j) for j in rows.scalars().all()]

        if self.cache:
            try:
                payload_to_cache = json.dumps(
                    {'items': [j.model_dump() for j in jobs], 'total_count': total}
                )
                await self.cache.set(cache_key, payload_to_cache, ex=DEFAULT_CACHE_TTL)
                logger.info(
                    f"[CACHE ASYNC SET] Client jobs list for {client_id} (skip={skip}, limit={limit})"
                )
            except Exception as e:
                logger.error(f"[CACHE ASYNC WRITE ERROR] Client jobs list {client_id}: {e}")
        return jobs, total

    async def get_job_detail(self, client_id: UUID, job_id: UUID) -> ClientJobRead:
        """Get detail of a specific job posted by the client."""
        await self._get_user(client_id, UserRole.CLIENT)
        res = await self.db.execute(select(Job).filter_by(id=job_id, client_id=client_id))
        job = res.scalar_one_or_none()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Job not found or unauthorized"
            )
        return ClientJobRead.model_validate(job)

    async def invalidate_job_cache(self, client_id: UUID) -> None:
        """Explicitly clear job list cache for a client."""
        await self._invalidate_paginated_cache(CLIENT_JOBS_NS, client_id)
