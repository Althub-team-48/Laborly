"""
client/services.py

Service class for handling all client-related business logic:
- Client profile retrieval and updates
- Managing favorite workers
- Fetching job history and job details
"""

import logging
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client import models, schemas
from app.core.upload import generate_presigned_url, get_s3_key_from_url
from app.database.enums import UserRole
from app.database.models import User
from app.job.models import Job

# ---------------------------------------------------
# Logger Setup
# ---------------------------------------------------
logger = logging.getLogger(__name__)


# ---------------------------------------------------
# Helper Functions (Keep as is)
# ---------------------------------------------------
def merge_user_profile(profile: models.ClientProfile, user: User) -> dict[str, Any]:
    """
    Combine user and profile attributes for unified response.
    Uses the User model directly now.
    """
    profile_data = {k: v for k, v in vars(profile).items() if not k.startswith("_")}
    user_data = {k: v for k, v in vars(user).items() if not k.startswith("_") and k in {
        "email", "phone_number", "first_name", "last_name", "location", "created_at", "updated_at"
    }}
    return {**user_data, **profile_data, "id": profile.id, "user_id": user.id}


# ---------------------------------------------------
# Service Class: ClientService
# ---------------------------------------------------
class ClientService:
    """
    Provides methods for handling client-specific operations.
    """

    def __init__(self, db: AsyncSession):
        """
        Initializes the service with an async database session.
        """
        self.db = db

    async def get_profile_picture_presigned_url(self, user_id: UUID) -> str | None:
        """
        Gets the user's profile picture S3 URL and returns a pre-signed URL for it.

        Returns:
            Optional[str]: The pre-signed URL or None if no picture is set or generation fails.
        """
        logger.info(f"Requesting pre-signed URL for profile picture of user_id={user_id}")
        user = await self._get_user_or_404(user_id)

        s3_full_url = user.profile_picture
        if not s3_full_url:
            logger.info(f"User {user_id} does not have a profile picture set.")
            return None

        s3_key = get_s3_key_from_url(s3_full_url)
        if not s3_key:
            logger.error(
                f"Could not extract S3 key from stored profile picture URL for user {user_id}: {s3_full_url}"
            )
            return None

        presigned_url = generate_presigned_url(s3_key, expiration=3600)
        if not presigned_url:
            logger.error(f"Failed to generate pre-signed URL for profile picture key: {s3_key}")
            return None

        return presigned_url

    async def _get_user_and_profile(self, user_id: UUID) -> tuple[User, models.ClientProfile]:
        """Fetches user and their client profile, creating profile if needed."""
        user = await self._get_user_or_404(user_id)

        profile_result = await self.db.execute(
            select(models.ClientProfile).filter(models.ClientProfile.user_id == user_id)
        )
        profile = profile_result.unique().scalar_one_or_none()

        if not profile:
            logger.info(f"No profile found. Creating new one for user_id={user_id}")
            profile = models.ClientProfile(user_id=user_id)
            self.db.add(profile)
            await self.db.flush()
            await self.db.refresh(profile)
            logger.info(f"New profile created: profile_id={profile.id}")

        return user, profile

    # ---------------------------------------------------
    # Profile Management
    # ---------------------------------------------------
    async def get_profile(self, user_id: UUID) -> schemas.ClientProfileRead:
        """
        Retrieve or create a client profile for the user.
        """
        logger.info(f"Retrieving client profile for user_id={user_id}")
        user, profile = await self._get_user_and_profile(user_id)
        merged_data = merge_user_profile(profile, user)
        return schemas.ClientProfileRead.model_validate(merged_data)

    async def update_profile(
        self, user_id: UUID, update_payload: schemas.ClientProfileUpdate
    ) -> schemas.ClientProfileRead:
        """
        Update user and profile fields for the client (excluding profile picture).
        """
        logger.info(f"Updating profile for user_id={user_id}")
        user, profile = await self._get_user_and_profile(user_id)

        update_data = update_payload.model_dump(exclude_unset=True)

        user_fields_to_update = ["first_name", "last_name", "location", "phone_number"]
        user_updated = False
        for attr in user_fields_to_update:
            if attr in update_data:
                setattr(user, attr, update_data[attr])
                user_updated = True

        profile_fields_to_update = ["profile_description", "address"]
        profile_updated = False
        for attr in profile_fields_to_update:
            if attr in update_data:
                setattr(profile, attr, update_data[attr])
                profile_updated = True

        if not user_updated and not profile_updated:
            logger.info(f"No fields to update for user_id={user_id}")
            merged_data = merge_user_profile(profile, user)
            return schemas.ClientProfileRead.model_validate(merged_data)

        try:
            await self.db.commit()
            if user_updated:
                await self.db.refresh(user)
            if profile_updated:
                await self.db.refresh(profile)
            logger.info(f"Profile updated for user_id={user_id}, profile_id={profile.id}")
        except Exception as e:
            logger.error(f"Error committing profile update for user {user_id}: {e}", exc_info=True)
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update profile.",
            )

        merged_data = merge_user_profile(profile, user)
        return schemas.ClientProfileRead.model_validate(merged_data)

    async def update_profile_picture(
        self, user_id: UUID, picture_url: str
    ) -> schemas.ClientProfileRead:
        """
        Updates only the profile picture URL on the User model.
        """
        logger.info(f"Updating profile picture for user_id={user_id} to {picture_url}")
        user, profile = await self._get_user_and_profile(user_id)

        if user.profile_picture == picture_url:
            logger.info(f"Profile picture for user {user_id} is already set to the provided URL.")
            merged_data = merge_user_profile(profile, user)
            return schemas.ClientProfileRead.model_validate(merged_data)

        user.profile_picture = picture_url

        try:
            await self.db.commit()
            await self.db.refresh(user)
        except Exception as e:
            logger.error(
                f"Error committing profile picture update for user {user_id}: {e}", exc_info=True
            )
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update profile picture.",
            )

        return schemas.ClientProfileRead.model_validate(merge_user_profile(profile, user))

    # ---------------------------------------------------
    # Favorite Worker Management
    # ---------------------------------------------------
    async def list_favorites(self, client_id: UUID) -> list[models.FavoriteWorker]:
        logger.info(f"Listing favorites for client_id={client_id}")
        result = await self.db.execute(
            select(models.FavoriteWorker).filter(models.FavoriteWorker.client_id == client_id)
        )
        return list(result.scalars().all())

    async def add_favorite(self, client_id: UUID, worker_id: UUID) -> models.FavoriteWorker:
        logger.info(f"Adding favorite: client_id={client_id}, worker_id={worker_id}")
        worker_exists = await self._get_user_or_404(worker_id)
        if worker_exists.role != UserRole.WORKER:
            raise HTTPException(
                status_code=400, detail="Can only favorite users with the WORKER role."
            )

        existing_favorite_result = await self.db.execute(
            select(models.FavoriteWorker).filter_by(client_id=client_id, worker_id=worker_id)
        )
        existing = existing_favorite_result.scalar_one_or_none()

        if existing:
            logger.warning(f"Worker {worker_id} already favorited by client {client_id}")
            raise HTTPException(status_code=400, detail="Worker already in favorites")

        favorite = models.FavoriteWorker(client_id=client_id, worker_id=worker_id)
        self.db.add(favorite)
        await self.db.commit()
        await self.db.refresh(favorite)

        logger.info(f"Favorite added: favorite_id={favorite.id}")
        return favorite

    async def remove_favorite(self, client_id: UUID, worker_id: UUID) -> None:
        logger.info(f"Removing favorite: client_id={client_id}, worker_id={worker_id}")
        favorite_to_remove_result = await self.db.execute(
            select(models.FavoriteWorker).filter_by(client_id=client_id, worker_id=worker_id)
        )
        favorite = favorite_to_remove_result.scalar_one_or_none()

        if not favorite:
            logger.warning(f"Favorite not found for client {client_id}, worker {worker_id}")
            raise HTTPException(status_code=404, detail="Favorite not found")

        await self.db.delete(favorite)
        await self.db.commit()
        logger.info("Favorite removed successfully")

    # ---------------------------------------------------
    # Job History
    # ---------------------------------------------------
    async def get_jobs(self, client_id: UUID) -> list[Job]:
        logger.info(f"Fetching job list for client_id={client_id}")
        result = await self.db.execute(
            select(Job).filter(Job.client_id == client_id).order_by(Job.created_at.desc())
        )
        return list(result.unique().scalars().all())

    async def get_job_detail(self, client_id: UUID, job_id: UUID) -> Job:
        logger.info(f"Fetching job detail: client_id={client_id}, job_id={job_id}")
        result = await self.db.execute(
            select(Job).filter(Job.id == job_id, Job.client_id == client_id)
            # Add options to load related data if needed by ClientJobRead schema
            # .options(selectinload(Job.worker), selectinload(Job.service))
        )
        job = result.unique().scalar_one_or_none()

        if not job:
            logger.warning(
                f"Job not found or unauthorized access: job_id={job_id}, client_id={client_id}"
            )
            raise HTTPException(status_code=404, detail="Job not found or unauthorized")

        logger.info(f"Job retrieved: job_id={job.id}")
        return job

    async def _get_user_or_404(self, user_id: UUID) -> User:
        """Helper method to retrieve a user or raise 404 if not found."""
        user = await self.db.get(User, user_id)
        if not user:
            logger.warning(f"[UTIL] User not found: user_id={user_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user
