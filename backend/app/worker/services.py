"""
backend/app/worker/services.py

Worker Service Layer (Corrected Async Redis Usage)
Handles core business logic for worker profile management, KYC processing,
profile picture handling, and job history operations. Enforces Pydantic model contracts.
Includes Redis caching for read operations and invalidation for write operations.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.blacklist import redis_client
from app.core.config import settings
from app.core.schemas import MessageResponse
from app.core.upload import generate_presigned_url, get_s3_key_from_url
from app.database.enums import KYCStatus, UserRole
from app.database.models import KYC, User
from app.job.models import Job
from app.job.schemas import JobRead
from app.worker import models, schemas

logger = logging.getLogger(__name__)

# --- Cache Configuration ---
CACHE_PREFIX = getattr(settings, 'CACHE_PREFIX', 'cache:laborly:')
DEFAULT_CACHE_TTL = getattr(settings, 'DEFAULT_CACHE_TTL', 3600)


# --- Helper Functions for Cache Keys ---
def _cache_key(namespace: str, identifier: Any) -> str:
    """Generate a simple cache key."""
    return f"{CACHE_PREFIX}{namespace}:{identifier}"


def _paginated_cache_key(namespace: str, identifier: Any, skip: int, limit: int) -> str:
    """Generate a cache key for paginated data."""
    return f"{CACHE_PREFIX}{namespace}:{identifier}:skip={skip}:limit={limit}"


class WorkerService:
    """Handles all worker-related operations, including caching and data access."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        if not redis_client:
            logger.warning("[CACHE] Redis client not configured, caching disabled.")
        self.cache = redis_client

    # --- Cache Invalidation ---
    async def _invalidate_worker_caches(self, user_id: UUID) -> None:
        """Invalidate all relevant worker-related cache keys."""
        if not self.cache:
            return
        keys = [
            _cache_key("worker_profile", user_id),
            _cache_key("public_worker_profile", user_id),
            _cache_key("worker_kyc", user_id),
        ]
        try:
            await self.cache.delete(*keys)  # type: ignore
            logger.debug(f"[CACHE] Invalidated keys: {keys}")
        except Exception as e:
            logger.error(f"[CACHE] Invalidation failed for {keys}: {e}")

    # --- Internal Helpers ---
    async def _get_user_or_404(self, user_id: UUID) -> User:
        """Fetch user or raise 404/403 errors for invalid cases."""
        user = await self.db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if user.role != UserRole.WORKER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="User is not a worker"
            )
        return user

    async def _get_user_and_profile(self, user_id: UUID) -> tuple[User, models.WorkerProfile]:
        """Fetch both User and WorkerProfile or create profile if missing."""
        user = await self._get_user_or_404(user_id)
        result = await self.db.execute(select(models.WorkerProfile).filter_by(user_id=user_id))
        profile = result.scalars().unique().one_or_none()

        if not profile:
            profile = models.WorkerProfile(user_id=user_id)
            self.db.add(profile)
            await self.db.flush()
            await self.db.refresh(profile)
            logger.info(f"[WORKER] Created worker profile for {user_id}")

        return user, profile

    def _merge_user_profile(self, user: User, profile: models.WorkerProfile) -> dict[str, Any]:
        """Merge user and worker profile data into one dictionary."""
        data = {k: v for k, v in vars(profile).items() if not k.startswith("_")}
        data.update(
            {
                "user_id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone_number": user.phone_number,
                "location": user.location,
                "profile_picture": user.profile_picture,
            }
        )
        return data

    # ---------------------------------------------
    # Worker Profile Methods (Authenticated)
    # ---------------------------------------------
    async def get_profile(self, user_id: UUID) -> schemas.WorkerProfileRead:
        """Get authenticated user's worker profile with caching."""
        cache_key = _cache_key("worker_profile", user_id)
        if self.cache:
            try:
                data = await self.cache.get(cache_key)  # type: ignore
                if data:
                    return schemas.WorkerProfileRead.model_validate_json(data)
            except Exception:
                logger.exception("[CACHE] Read error")

        user, profile = await self._get_user_and_profile(user_id)
        merged = self._merge_user_profile(user, profile)
        response = schemas.WorkerProfileRead.model_validate(merged)

        if self.cache:
            try:
                await self.cache.set(cache_key, response.model_dump_json(), ex=DEFAULT_CACHE_TTL)  # type: ignore
            except Exception:
                logger.exception("[CACHE] Write error")

        return response

    async def update_profile(
        self, user_id: UUID, data: schemas.WorkerProfileUpdate
    ) -> schemas.WorkerProfileRead:
        """Update worker profile and user fields."""
        await self._invalidate_worker_caches(user_id)
        user, profile = await self._get_user_and_profile(user_id)
        updates = data.model_dump(exclude_unset=True)

        # Update user fields
        for field in {"first_name", "last_name", "phone_number", "location"} & updates.keys():
            setattr(user, field, updates[field])
        # Update profile fields
        for field in {
            "bio",
            "years_experience",
            "availability_note",
            "is_available",
            "professional_skills",
            "work_experience",
        } & updates.keys():
            setattr(profile, field, updates[field])

        try:
            await self.db.commit()
            await self.db.refresh(user)
            await self.db.refresh(profile)
        except Exception:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail="Failed to update profile.")

        merged = self._merge_user_profile(user, profile)
        response = schemas.WorkerProfileRead.model_validate(merged)

        if self.cache:
            try:
                await self.cache.set(_cache_key("worker_profile", user_id), response.model_dump_json(), ex=DEFAULT_CACHE_TTL)  # type: ignore
            except Exception:
                logger.exception("[CACHE] Post-update write error")

        return response

    async def update_profile_picture(self, user_id: UUID, picture_url: str) -> MessageResponse:
        """Update the profile picture of a worker."""
        await self._invalidate_worker_caches(user_id)
        user, _ = await self._get_user_and_profile(user_id)
        if user.profile_picture != picture_url:
            user.profile_picture = picture_url
            try:
                await self.db.commit()
                await self.db.refresh(user)
            except Exception:
                await self.db.rollback()
                raise HTTPException(status_code=500, detail="Failed to update profile picture.")

        return MessageResponse(detail="Profile picture updated successfully.")

    # ---------------------------------------------
    # Profile Picture (Authenticated)
    # ---------------------------------------------
    async def get_profile_picture_presigned_url(self, user_id: UUID) -> str | None:
        logger.info(f"Generating presigned URL for user {user_id}")
        user = await self._get_user_or_404(user_id)
        if not user.profile_picture:
            return None
        key = get_s3_key_from_url(user.profile_picture)
        if not key:
            logger.error(f"Invalid profile picture URL for user {user_id}")
            return None
        return generate_presigned_url(key, expiration=3600)

    # ---------------------------------------------
    # Worker Profile Methods (Public)
    # ---------------------------------------------
    async def get_public_worker_profile(self, user_id: UUID) -> schemas.PublicWorkerRead:
        """Return publicly available information about a worker."""
        cache_key = _cache_key("public_worker_profile", user_id)
        if self.cache:
            try:
                data = await self.cache.get(cache_key)  # type: ignore
                if data:
                    return schemas.PublicWorkerRead.model_validate_json(data)
            except Exception:
                logger.exception("[CACHE] Read error")

        user = await self.db.get(User, user_id)
        if not user or user.role != UserRole.WORKER:
            raise HTTPException(status_code=404, detail="Worker profile not found")

        result = await self.db.execute(select(models.WorkerProfile).filter_by(user_id=user_id))
        profile = result.scalars().unique().one_or_none()
        if not profile:
            raise HTTPException(status_code=404, detail="Worker profile data not found")

        data = self._merge_user_profile(user, profile)
        public_data = {
            k: data[k]
            for k in (
                "user_id",
                "first_name",
                "last_name",
                "location",
                "profile_picture",
                "professional_skills",
                "work_experience",
                "years_experience",
                "bio",
                "is_available",
            )
        }
        response = schemas.PublicWorkerRead.model_validate(public_data)

        if self.cache:
            try:
                await self.cache.set(cache_key, response.model_dump_json(), ex=DEFAULT_CACHE_TTL)  # type: ignore
            except Exception:
                logger.exception("[CACHE] Write error")

        return response

    # ---------------------------------------------
    # Availability Toggle
    # ---------------------------------------------
    async def toggle_availability(
        self, user_id: UUID, payload: schemas.WorkerProfileUpdate
    ) -> schemas.WorkerProfileRead:
        """Toggle availability status for a worker."""
        await self._invalidate_worker_caches(user_id)
        _, profile = await self._get_user_and_profile(user_id)
        if payload.is_available is None:
            raise HTTPException(status_code=400, detail="Availability status must be provided.")
        if profile.is_available != payload.is_available:
            profile.is_available = payload.is_available
            try:
                await self.db.commit()
                await self.db.refresh(profile)
            except Exception:
                await self.db.rollback()
                raise HTTPException(status_code=500, detail="Failed to update availability.")

        return await self.get_profile(user_id)

    # ---------------------------------------------
    # KYC Management Methods
    # ---------------------------------------------
    async def get_kyc(self, user_id: UUID) -> schemas.KYCRead | None:
        """Retrieve the worker's KYC data with cache support."""
        cache_key = _cache_key("worker_kyc", user_id)
        if self.cache:
            try:
                data = await self.cache.get(cache_key)  # type: ignore
                if data:
                    return schemas.KYCRead.model_validate_json(data) if data != "null" else None
            except Exception:
                logger.exception("[CACHE] Read error")

        await self._get_user_or_404(user_id)
        result = await self.db.execute(select(KYC).filter_by(user_id=user_id))
        kyc = result.scalars().unique().one_or_none()
        response = schemas.KYCRead.model_validate(kyc) if kyc else None

        if self.cache:
            try:
                to_cache = response.model_dump_json() if response else "null"
                await self.cache.set(cache_key, to_cache, ex=DEFAULT_CACHE_TTL)  # type: ignore
            except Exception:
                logger.exception("[CACHE] Write error")

        return response

    async def submit_kyc(self, user_id: UUID, kyc_data: schemas.KYCRead) -> schemas.KYCRead:
        """Submit or update a worker's KYC information."""
        await self._invalidate_worker_caches(user_id)
        await self._get_user_or_404(user_id)
        result = await self.db.execute(select(KYC).filter_by(user_id=user_id))
        kyc = result.scalars().unique().one_or_none()
        now = datetime.now(timezone.utc)

        if not kyc:
            kyc = KYC(
                user_id=user_id,
                **kyc_data.model_dump(exclude_unset=True),
                submitted_at=now,
                status=KYCStatus.PENDING,
            )
            self.db.add(kyc)
        else:
            for field in ("document_type", "document_path", "selfie_path"):
                setattr(kyc, field, getattr(kyc_data, field))
            kyc.submitted_at = now
            kyc.status = KYCStatus.PENDING
            kyc.reviewed_at = None

        try:
            await self.db.commit()
            await self.db.refresh(kyc)
        except Exception:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail="Failed to submit KYC.")

        response = schemas.KYCRead.model_validate(kyc)
        if self.cache:
            try:
                await self.cache.set(_cache_key("worker_kyc", user_id), response.model_dump_json(), ex=DEFAULT_CACHE_TTL)  # type: ignore
            except Exception:
                logger.exception("[CACHE] Write error")

        return response

    # ---------------------------------------------
    # Job Management Methods
    # ---------------------------------------------
    async def get_jobs(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[JobRead], int]:
        """Retrieve paginated list of jobs assigned to the worker."""
        cache_key = _paginated_cache_key("worker_jobs", user_id, skip, limit)
        if self.cache:
            try:
                data = await self.cache.get(cache_key)  # type: ignore
                if data:
                    payload = json.loads(data)
                    items = [JobRead.model_validate(i) for i in payload["items"]]
                    return items, payload["total_count"]
            except Exception:
                logger.exception("[CACHE] Read error")

        await self._get_user_or_404(user_id)
        total = (
            await self.db.execute(select(func.count(Job.id)).filter_by(worker_id=user_id))
        ).scalar_one()
        rows = await self.db.execute(
            select(Job)
            .filter_by(worker_id=user_id)
            .order_by(Job.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        jobs = rows.scalars().unique().all()
        reads = [JobRead.model_validate(j) for j in jobs]

        if self.cache:
            try:
                payload = json.dumps(
                    {"items": [r.model_dump() for r in reads], "total_count": total}
                )
                await self.cache.set(cache_key, payload, ex=DEFAULT_CACHE_TTL)  # type: ignore
            except Exception:
                logger.exception("[CACHE] Write error")

        return reads, total

    async def get_job_detail(self, user_id: UUID, job_id: UUID) -> JobRead:
        """Get detailed information about a specific job for the worker."""
        await self._get_user_or_404(user_id)
        row = await self.db.execute(select(Job).filter_by(id=job_id, worker_id=user_id))
        job = row.scalars().unique().one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found or unauthorized")
        return JobRead.model_validate(job)
