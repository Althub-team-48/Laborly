"""
client/services.py

Service class for handling all client-related business logic:
- Client profile retrieval and updates
- Managing favorite workers
- Fetching job history and job details
"""

# ---------------------------------------------------
# Imports
# ---------------------------------------------------

import logging
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client import models, schemas
from app.database.models import User
from app.job.models import Job

# ---------------------------------------------------
# Logger Setup
# ---------------------------------------------------

logger = logging.getLogger(__name__)

# ---------------------------------------------------
# Helper Functions
# ---------------------------------------------------


def merge_user_profile(profile: models.ClientProfile, user: User) -> dict[str, Any]:
    """
    Combine user and profile attributes for unified response.
    """
    return {
        **{k: v for k, v in vars(profile).items() if not k.startswith("_")},
        "email": user.email,
        "phone_number": user.phone_number,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "location": user.location,
        "profile_picture": user.profile_picture,
        "updated_at": user.updated_at,
    }


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

    # ---------------------------------------------------
    # Profile Management
    # ---------------------------------------------------

    async def get_profile(self, user_id: UUID) -> schemas.ClientProfileRead:
        """
        Retrieve or create a client profile for the user.
        """
        logger.info(f"Retrieving client profile for user_id={user_id}")
        user_result = await self.db.execute(select(User).filter(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            logger.warning(f"User not found: user_id={user_id}")
            raise HTTPException(status_code=404, detail="User not found")

        profile_result = await self.db.execute(
            select(models.ClientProfile).filter(models.ClientProfile.user_id == user_id)
        )
        profile = profile_result.scalar_one_or_none()

        if not profile:
            logger.info(f"No profile found. Creating new one for user_id={user_id}")
            profile = models.ClientProfile(user_id=user_id)
            self.db.add(profile)
            await self.db.commit()
            await self.db.refresh(profile)
            logger.info(f"New profile created: profile_id={profile.id}")

        merged_data = merge_user_profile(profile, user)
        return schemas.ClientProfileRead.model_validate(merged_data)

    async def update_profile(
        self, user_id: UUID, update: schemas.ClientProfileUpdate
    ) -> schemas.ClientProfileRead:
        """
        Update both user and profile fields for the client.
        """
        logger.info(f"Updating profile for user_id={user_id}")
        user_result = await self.db.execute(select(User).filter(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            logger.warning(f"User not found: user_id={user_id}")
            raise HTTPException(status_code=404, detail="User not found")

        profile_result = await self.db.execute(
            select(models.ClientProfile).filter(models.ClientProfile.user_id == user_id)
        )
        profile = profile_result.scalar_one_or_none()
        if not profile:
            logger.warning(f"Profile not found: user_id={user_id}")
            raise HTTPException(status_code=404, detail="Client profile not found")

        update_data = update.model_dump(exclude_unset=True)

        user_fields_to_update = ["first_name", "last_name", "location", "profile_picture"]
        for attr in user_fields_to_update:
            if attr in update_data:
                setattr(user, attr, update_data[attr])
                # Removed debug log: logger.debug(...)

        profile_fields_to_update = ["business_name"]
        for attr in profile_fields_to_update:
            if attr in update_data:
                setattr(profile, attr, update_data[attr])
                # Removed debug log: logger.debug(...)

        await self.db.commit()
        await self.db.refresh(user)
        await self.db.refresh(profile)

        logger.info(f"Profile updated for user_id={user_id}, profile_id={profile.id}")
        merged_data = merge_user_profile(profile, user)
        return schemas.ClientProfileRead.model_validate(merged_data)

    # ---------------------------------------------------
    # Favorite Worker Management
    # ---------------------------------------------------

    async def list_favorites(self, client_id: UUID) -> list[models.FavoriteWorker]:
        """
        Retrieve all favorite workers saved by the client.
        """
        logger.info(f"Listing favorites for client_id={client_id}")
        result = await self.db.execute(
            select(models.FavoriteWorker).filter(models.FavoriteWorker.client_id == client_id)
        )
        return list(result.scalars())

    async def add_favorite(self, client_id: UUID, worker_id: UUID) -> models.FavoriteWorker:
        """
        Add a worker to the client's list of favorites.
        """
        logger.info(f"Adding favorite: client_id={client_id}, worker_id={worker_id}")
        existing_favorite_result = await self.db.execute(
            select(models.FavoriteWorker).filter(
                models.FavoriteWorker.client_id == client_id,
                models.FavoriteWorker.worker_id == worker_id,
            )
        )
        existing = existing_favorite_result.scalar_one_or_none()

        if existing:
            logger.warning("Worker already favorited")
            raise HTTPException(status_code=400, detail="Worker already in favorites")

        favorite = models.FavoriteWorker(client_id=client_id, worker_id=worker_id)
        self.db.add(favorite)
        await self.db.commit()
        await self.db.refresh(favorite)

        logger.info(f"Favorite added: favorite_id={favorite.id}")
        return favorite

    async def remove_favorite(self, client_id: UUID, worker_id: UUID) -> None:
        """
        Remove a worker from the client's favorites list.
        """
        logger.info(f"Removing favorite: client_id={client_id}, worker_id={worker_id}")
        favorite_to_remove_result = await self.db.execute(
            select(models.FavoriteWorker).filter(
                models.FavoriteWorker.client_id == client_id,
                models.FavoriteWorker.worker_id == worker_id,
            )
        )
        favorite = favorite_to_remove_result.scalar_one_or_none()

        if not favorite:
            logger.warning("Favorite not found")
            raise HTTPException(status_code=404, detail="Favorite not found")

        await self.db.delete(favorite)
        await self.db.commit()
        logger.info("Favorite removed successfully")
        # Explicit return None is good practice for functions declared to return None
        return None

    # ---------------------------------------------------
    # Job History
    # ---------------------------------------------------

    async def get_jobs(self, client_id: UUID) -> list[Job]:
        """
        Retrieve all jobs created by the client.
        """
        logger.info(f"Fetching job list for client_id={client_id}")
        result = await self.db.execute(select(Job).filter(Job.client_id == client_id))
        return list(result.scalars())

    async def get_job_detail(self, client_id: UUID, job_id: UUID) -> Job:
        """
        Retrieve detailed info about a job created by the client.
        """
        logger.info(f"Fetching job detail: client_id={client_id}, job_id={job_id}")
        result = await self.db.execute(
            select(Job).filter(Job.id == job_id, Job.client_id == client_id)
        )
        job = result.scalar_one_or_none()

        if not job:
            logger.warning("Job not found or unauthorized access")
            raise HTTPException(status_code=404, detail="Job not found or unauthorized")

        logger.info(f"Job retrieved: job_id={job.id}")
        return job
