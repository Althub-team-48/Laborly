"""
backend/app/client/services.py

Client Service Layer
Handles client-specific business logic including:
- Client profile management (authenticated and public views)
- Favorite worker management
- Client job history retrieval
"""

import logging
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.client import models, schemas
from app.core.upload import generate_presigned_url, get_s3_key_from_url
from app.database.enums import UserRole
from app.database.models import User
from app.job.models import Job

logger = logging.getLogger(__name__)


def merge_user_profile(profile: models.ClientProfile, user: User) -> dict[str, Any]:
    """Combine user and profile attributes for a unified response."""
    profile_data = {k: v for k, v in vars(profile).items() if not k.startswith("_")}
    user_data = {
        k: v
        for k, v in vars(user).items()
        if not k.startswith("_")
        and k
        in {
            "email",
            "phone_number",
            "first_name",
            "last_name",
            "location",
            "created_at",
            "updated_at",
        }
    }
    return {**user_data, **profile_data, "id": profile.id, "user_id": user.id}


class ClientService:
    """Service class providing methods to manage client-specific operations."""

    def __init__(self, db: AsyncSession):
        """Initialize with an async database session."""
        self.db = db

    # ---------------------------------------------------
    # Utility Methods
    # ---------------------------------------------------
    async def _get_user_or_404(self, user_id: UUID) -> User:
        """Retrieve a user or raise 404 if not found."""
        user = await self.db.get(User, user_id)
        if not user:
            logger.warning(f"User not found: user_id={user_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    async def _get_user_and_profile(self, user_id: UUID) -> tuple[User, models.ClientProfile]:
        """Fetch user and their client profile; create profile if it does not exist."""
        user = await self._get_user_or_404(user_id)
        profile_result = await self.db.execute(
            select(models.ClientProfile).filter(models.ClientProfile.user_id == user_id)
        )
        profile = profile_result.unique().scalar_one_or_none()

        if not profile:
            logger.info(f"Creating new client profile for user_id={user_id}")
            profile = models.ClientProfile(user_id=user_id)
            self.db.add(profile)
            await self.db.flush()
            await self.db.refresh(profile)

        return user, profile

    async def get_profile_picture_presigned_url(self, user_id: UUID) -> str | None:
        """Generate a pre-signed URL for the client's profile picture."""
        logger.info(f"Requesting pre-signed URL for user_id={user_id}")
        user = await self._get_user_or_404(user_id)

        if not user.profile_picture:
            logger.info(f"No profile picture set for user_id={user_id}")
            return None

        s3_key = get_s3_key_from_url(user.profile_picture)
        if not s3_key:
            logger.error(f"Failed to extract S3 key for user_id={user_id}")
            return None

        presigned_url = generate_presigned_url(s3_key, expiration=3600)
        if not presigned_url:
            logger.error(f"Failed to generate pre-signed URL for S3 key: {s3_key}")
            return None

        return presigned_url

    # ---------------------------------------------------
    # Client Profile Management (Authenticated)
    # ---------------------------------------------------
    async def get_profile(self, user_id: UUID) -> schemas.ClientProfileRead:
        """Retrieve or create a client profile for the authenticated user."""
        logger.info(f"Fetching client profile for user_id={user_id}")
        user, profile = await self._get_user_and_profile(user_id)
        return schemas.ClientProfileRead.model_validate(merge_user_profile(profile, user))

    async def update_profile(
        self, user_id: UUID, update_payload: schemas.ClientProfileUpdate
    ) -> schemas.ClientProfileRead:
        """Update user and client profile fields (excluding profile picture)."""
        logger.info(f"Updating profile for user_id={user_id}")
        user, profile = await self._get_user_and_profile(user_id)
        update_data = update_payload.model_dump(exclude_unset=True)

        user_fields = ["first_name", "last_name", "location", "phone_number"]
        profile_fields = ["profile_description", "address"]

        user_updated = False
        for field in user_fields:
            if field in update_data:
                setattr(user, field, update_data[field])
                user_updated = True

        profile_updated = False
        for field in profile_fields:
            if field in update_data:
                setattr(profile, field, update_data[field])
                profile_updated = True

        if not user_updated and not profile_updated:
            logger.info(f"No fields to update for user_id={user_id}")
            return schemas.ClientProfileRead.model_validate(merge_user_profile(profile, user))

        try:
            await self.db.commit()
            if user_updated:
                await self.db.refresh(user)
            if profile_updated:
                await self.db.refresh(profile)
        except Exception as e:
            logger.error(f"Error updating profile for user_id={user_id}: {e}", exc_info=True)
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update profile.",
            )

        return schemas.ClientProfileRead.model_validate(merge_user_profile(profile, user))

    async def update_profile_picture(
        self, user_id: UUID, picture_url: str
    ) -> schemas.ClientProfileRead:
        """Update the profile picture URL for the authenticated client."""
        logger.info(f"Updating profile picture for user_id={user_id}")
        user, profile = await self._get_user_and_profile(user_id)

        if user.profile_picture == picture_url:
            logger.info(f"Profile picture for user_id={user_id} already set.")
            return schemas.ClientProfileRead.model_validate(merge_user_profile(profile, user))

        user.profile_picture = picture_url

        try:
            await self.db.commit()
            await self.db.refresh(user)
        except Exception as e:
            logger.error(
                f"Error updating profile picture for user_id={user_id}: {e}", exc_info=True
            )
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update profile picture.",
            )

        return schemas.ClientProfileRead.model_validate(merge_user_profile(profile, user))

    # ---------------------------------------------------
    # Client Profile Management (Public)
    # ---------------------------------------------------
    async def get_public_client_profile(self, user_id: UUID) -> schemas.PublicClientRead:
        """Retrieve public view of a client profile."""
        logger.info(f"Fetching public profile for user_id={user_id}")
        user = await self.db.get(User, user_id)

        if not user or user.role != UserRole.CLIENT:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

        profile_result = await self.db.execute(
            select(models.ClientProfile).filter(models.ClientProfile.user_id == user_id)
        )
        profile = profile_result.unique().scalar_one_or_none()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Client profile not found"
            )

        public_data = {
            "user_id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "location": user.location,
        }
        return schemas.PublicClientRead.model_validate(public_data)

    # ---------------------------------------------------
    # Favorite Worker Management (Authenticated Client)
    # ---------------------------------------------------
    async def list_favorites(
        self, client_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[models.FavoriteWorker], int]:
        """List all favorite workers for the authenticated client with pagination and total count."""
        logger.info(f"Listing favorite workers for client_id={client_id}")

        # Count total records
        count_stmt = select(func.count()).filter(models.FavoriteWorker.client_id == client_id)
        total_count_result = await self.db.execute(count_stmt)
        total_count = total_count_result.scalar_one()

        # Fetch paginated records
        result = await self.db.execute(
            select(models.FavoriteWorker)
            .filter(models.FavoriteWorker.client_id == client_id)
            .offset(skip)
            .limit(limit)
        )
        favorites = list(result.scalars().all())

        return favorites, total_count

    async def add_favorite(self, client_id: UUID, worker_id: UUID) -> models.FavoriteWorker:
        """Add a worker to the authenticated client's favorites."""
        logger.info(f"Adding favorite worker_id={worker_id} for client_id={client_id}")
        worker = await self._get_user_or_404(worker_id)

        if worker.role != UserRole.WORKER:
            raise HTTPException(
                status_code=400, detail="Can only favorite users with the WORKER role."
            )

        existing_result = await self.db.execute(
            select(models.FavoriteWorker).filter_by(client_id=client_id, worker_id=worker_id)
        )
        if existing_result.scalar_one_or_none():
            logger.warning(
                f"Favorite already exists for client_id={client_id}, worker_id={worker_id}"
            )
            raise HTTPException(status_code=400, detail="Worker already favorited.")

        favorite = models.FavoriteWorker(client_id=client_id, worker_id=worker_id)
        self.db.add(favorite)
        await self.db.commit()
        await self.db.refresh(favorite)
        logger.info(f"Favorite added successfully: favorite_id={favorite.id}")

        return favorite

    async def remove_favorite(self, client_id: UUID, worker_id: UUID) -> None:
        """Remove a worker from the authenticated client's favorites."""
        logger.info(f"Removing favorite worker_id={worker_id} for client_id={client_id}")
        result = await self.db.execute(
            select(models.FavoriteWorker).filter_by(client_id=client_id, worker_id=worker_id)
        )
        favorite = result.scalar_one_or_none()

        if not favorite:
            raise HTTPException(status_code=404, detail="Favorite not found.")

        await self.db.delete(favorite)
        await self.db.commit()
        logger.info("Favorite removed successfully.")

    # ---------------------------------------------------
    # Job History (Authenticated Client)
    # ---------------------------------------------------
    async def get_jobs(
        self, client_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[Job], int]:
        """Retrieve list of jobs posted by the authenticated client with pagination and total count."""
        logger.info(f"Fetching jobs for client_id={client_id}")

        # Count total records
        count_stmt = select(func.count()).filter(Job.client_id == client_id)
        total_count_result = await self.db.execute(count_stmt)
        total_count = total_count_result.scalar_one()

        # Fetch paginated records
        result = await self.db.execute(
            select(Job)
            .filter(Job.client_id == client_id)
            .order_by(Job.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        jobs = list(result.unique().scalars().all())

        logger.info(f"Found {len(jobs)} job(s) for client_id={client_id} (Total: {total_count}).")
        return jobs, total_count

    async def get_job_detail(self, client_id: UUID, job_id: UUID) -> Job:
        """Retrieve detailed information about a specific job posted by the client."""
        logger.info(f"Fetching job detail for job_id={job_id}, client_id={client_id}")
        result = await self.db.execute(
            select(Job).filter(Job.id == job_id, Job.client_id == client_id)
        )
        job = result.unique().scalar_one_or_none()

        if not job:
            logger.warning(
                f"Job not found or unauthorized access for client_id={client_id}, job_id={job_id}"
            )
            raise HTTPException(status_code=404, detail="Job not found or unauthorized")

        return job
