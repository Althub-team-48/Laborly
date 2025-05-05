"""
backend/app/client/services.py

Client Service Layer
Handles client profile operations, job management, favorites handling,
and profile picture utilities. Leverages Redis for caching where available.
"""

import json
import logging
from typing import Any
from uuid import UUID

from fastapi import HTTPException
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
from app.worker.services import _cache_key, _paginated_cache_key, DEFAULT_CACHE_TTL

logger = logging.getLogger(__name__)


# --- Cache Namespacing ---
def _ns_key(ns: str, identifier: UUID) -> str:
    """Helper to namespace cache keys consistently for clients."""
    return _cache_key(ns, identifier)


# --- Utility Functions ---
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
            'created_at': user.created_at,
            'updated_at': user.updated_at,
        }
    )
    return data


class ClientService:
    """Service class for client operations with caching and database support."""

    def __init__(self, db: AsyncSession):
        self.db = db
        if not redis_client:
            logger.warning("[CACHE] Redis client not configured, caching disabled.")
        self.cache = redis_client

    async def _invalidate_caches(self, user_id: UUID) -> None:
        """Remove user-related cache entries for client profile."""
        if not self.cache:
            return
        keys = [
            _ns_key('client_profile', user_id),
            _ns_key('public_client_profile', user_id),
        ]
        await self.cache.delete(*keys)

    async def _invalidate_paginated(self, ns: str, user_id: UUID) -> None:
        """Invalidate paginated cache entries based on namespace and user ID."""
        if not self.cache:
            return
        pattern = f"{DEFAULT_CACHE_TTL}{ns}:{user_id}:*"
        async for key in self.cache.scan_iter(match=pattern):
            await self.cache.delete(key)

    async def _get_user(self, user_id: UUID, role: UserRole) -> User:
        """Fetch a user and validate role."""
        user = await self.db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.role != role:
            raise HTTPException(status_code=403, detail=f"User is not {role.name.lower()}")
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
        cache_key = _ns_key('client_profile', user_id)
        if self.cache:
            try:
                data = await self.cache.get(cache_key)
                if data:
                    return schemas.ClientProfileRead.model_validate_json(data)
            except Exception:
                logger.exception("[CACHE] Read error")

        user, profile = await self._get_user_and_profile(user_id, UserRole.CLIENT)
        merged = _merge_client_profile(user, profile)
        response = schemas.ClientProfileRead.model_validate(merged)

        if self.cache:
            try:
                await self.cache.set(cache_key, response.model_dump_json(), ex=DEFAULT_CACHE_TTL)
            except Exception:
                logger.exception("[CACHE] Write error")
        return response

    async def update_profile(
        self, user_id: UUID, payload: schemas.ClientProfileUpdate
    ) -> schemas.ClientProfileRead:
        """Update the client’s profile and user details."""
        await self._invalidate_caches(user_id)
        user, profile = await self._get_user_and_profile(user_id, UserRole.CLIENT)
        data = payload.model_dump(exclude_unset=True)

        # Update user fields
        for f in {'first_name', 'last_name', 'location', 'phone_number'} & data.keys():
            setattr(user, f, data[f])
        # Update profile fields
        for f in {'profile_description', 'address'} & data.keys():
            setattr(profile, f, data[f])

        try:
            await self.db.commit()
            await self.db.refresh(user)
            await self.db.refresh(profile)
        except Exception:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail="Failed to update profile")
        return await self.get_profile(user_id)

    async def update_profile_picture(self, user_id: UUID, picture_url: str) -> MessageResponse:
        """Update the client's profile picture."""
        await self._invalidate_caches(user_id)
        user, _ = await self._get_user_and_profile(user_id, UserRole.CLIENT)
        if user.profile_picture != picture_url:
            user.profile_picture = picture_url
            try:
                await self.db.commit()
            except Exception:
                await self.db.rollback()
                raise HTTPException(status_code=500, detail="Failed to update picture")
        return MessageResponse(detail="Profile picture updated successfully.")

    # ---------------------------------------------------
    # Public Client Profile
    # ---------------------------------------------------
    async def get_public_client_profile(self, user_id: UUID) -> schemas.PublicClientRead:
        """Return limited public information for a client."""
        cache_key = _ns_key('public_client_profile', user_id)
        if self.cache:
            try:
                data = await self.cache.get(cache_key)
                if data:
                    return schemas.PublicClientRead.model_validate_json(data)
            except Exception:
                logger.exception("[CACHE] Read error")

        user = await self.db.get(User, user_id)
        if not user or user.role != UserRole.CLIENT:
            raise HTTPException(status_code=404, detail="Client not found")

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
            except Exception:
                logger.exception("[CACHE] Write error")
        return response

    # ---------------------------------------------------
    # Favorites (Authenticated)
    # ---------------------------------------------------
    async def list_favorites(
        self, client_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[FavoriteRead], int]:
        """Retrieve list of a client's favorite workers with cache support."""
        cache_key = _paginated_cache_key('client_favorites', client_id, skip, limit)
        if self.cache:
            try:
                data = await self.cache.get(cache_key)
                if data:
                    payload = json.loads(data)
                    items = [FavoriteRead.model_validate(i) for i in payload['items']]
                    return items, payload['total_count']
            except Exception:
                logger.exception("[CACHE] Read error")

        await self._get_user(client_id, UserRole.CLIENT)
        total = (
            await self.db.execute(
                select(func.count(models.FavoriteWorker.id)).filter_by(client_id=client_id)
            )
        ).scalar_one()
        rows = await self.db.execute(
            select(models.FavoriteWorker).filter_by(client_id=client_id).offset(skip).limit(limit)
        )
        favs = [FavoriteRead.model_validate(f) for f in rows.scalars().all()]

        if self.cache:
            try:
                payload = json.dumps(
                    {'items': [f.model_dump() for f in favs], 'total_count': total}
                )
                await self.cache.set(cache_key, payload, ex=DEFAULT_CACHE_TTL)
            except Exception:
                logger.exception("[CACHE] Write error")
        return favs, total

    async def add_favorite(self, client_id: UUID, worker_id: UUID) -> FavoriteRead:
        """Add a worker to a client's favorites."""
        await self._invalidate_paginated('client_favorites', client_id)
        await self._get_user(client_id, UserRole.CLIENT)
        await self._get_user(worker_id, UserRole.WORKER)

        exists = await self.db.execute(
            select(models.FavoriteWorker).filter_by(client_id=client_id, worker_id=worker_id)
        )
        if exists.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Already favorited")

        fav = models.FavoriteWorker(client_id=client_id, worker_id=worker_id)
        self.db.add(fav)
        try:
            await self.db.commit()
            await self.db.refresh(fav)
        except Exception:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail="Failed to add favorite")
        return FavoriteRead.model_validate(fav)

    async def remove_favorite(self, client_id: UUID, worker_id: UUID) -> None:
        """Remove a worker from a client’s favorites list."""
        await self._invalidate_paginated('client_favorites', client_id)
        await self._get_user(client_id, UserRole.CLIENT)

        res = await self.db.execute(
            select(models.FavoriteWorker).filter_by(client_id=client_id, worker_id=worker_id)
        )
        fav = res.scalar_one_or_none()
        if not fav:
            raise HTTPException(status_code=404, detail="Favorite not found")

        try:
            await self.db.delete(fav)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail="Failed to remove favorite")

    # ---------------------------------------------------
    # Job History (Authenticated)
    # ---------------------------------------------------
    async def get_jobs(
        self, client_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[ClientJobRead], int]:
        """Fetch jobs posted by the client."""
        cache_key = _paginated_cache_key('client_jobs', client_id, skip, limit)
        if self.cache:
            try:
                data = await self.cache.get(cache_key)
                if data:
                    payload = json.loads(data)
                    items = [ClientJobRead.model_validate(i) for i in payload['items']]
                    return items, payload['total_count']
            except Exception:
                logger.exception("[CACHE] Read error")

        await self._get_user(client_id, UserRole.CLIENT)
        total = (
            await self.db.execute(select(func.count(Job.id)).filter_by(client_id=client_id))
        ).scalar_one()
        rows = await self.db.execute(
            select(Job).filter_by(client_id=client_id).offset(skip).limit(limit)
        )
        jobs = [ClientJobRead.model_validate(j) for j in rows.scalars().all()]

        if self.cache:
            try:
                payload = json.dumps(
                    {'items': [j.model_dump() for j in jobs], 'total_count': total}
                )
                await self.cache.set(cache_key, payload, ex=DEFAULT_CACHE_TTL)
            except Exception:
                logger.exception("[CACHE] Write error")
        return jobs, total

    async def get_job_detail(self, client_id: UUID, job_id: UUID) -> ClientJobRead:
        """Get detail of a specific job posted by the client."""
        await self._get_user(client_id, UserRole.CLIENT)
        res = await self.db.execute(select(Job).filter_by(id=job_id, client_id=client_id))
        job = res.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found or unauthorized")
        return ClientJobRead.model_validate(job)

    async def invalidate_job_cache(self, client_id: UUID) -> None:
        """Explicitly clear job list cache for a client."""
        await self._invalidate_paginated('client_jobs', client_id)
