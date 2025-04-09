"""
client/services.py

Service class for handling all client-related business logic:
- Client profile retrieval and updates
- Managing favorite workers
- Fetching job history and job details
"""

import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client import models, schemas
from app.database.models import User
from app.job.models import Job

logger = logging.getLogger(__name__)


class ClientService:
    """
    Provides methods for handling client-specific operations.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # -------------------------------
    # Client Profile Management
    # -------------------------------

    async def get_profile(self, user_id: UUID) -> schemas.ClientProfileRead:
        """
        Retrieve or create a client profile for the user.
        """
        logger.info(f"Retrieving client profile for user_id={user_id}")

        user = (await self.db.execute(
            select(User).filter(User.id == user_id))
        ).scalar_one_or_none()

        if not user:
            logger.warning(f"User not found: user_id={user_id}")
            raise HTTPException(status_code=404, detail="User not found")

        profile = (await self.db.execute(
            select(models.ClientProfile).filter(models.ClientProfile.user_id == user_id))
        ).scalar_one_or_none()

        if not profile:
            logger.info(f"No profile found. Creating new one for user_id={user_id}")
            profile = models.ClientProfile(user_id=user_id)
            self.db.add(profile)
            await self.db.commit()
            await self.db.refresh(profile)
            logger.info(f"New profile created: profile_id={profile.id}")

        merged = {
            **{k: v for k, v in vars(profile).items() if not k.startswith("_")},
            **{k: v for k, v in vars(user).items() if not k.startswith("_")}
        }
        return schemas.ClientProfileRead.model_validate(merged)

    async def update_profile(self, user_id: UUID, update: schemas.ClientProfileUpdate) -> schemas.ClientProfileRead:
        """
        Update both user and profile fields for the client.
        """
        logger.info(f"Updating profile for user_id={user_id}")

        user = (await self.db.execute(
            select(User).filter(User.id == user_id))
        ).scalar_one_or_none()

        profile = (await self.db.execute(
            select(models.ClientProfile).filter(models.ClientProfile.user_id == user_id))
        ).scalar_one_or_none()

        if not user:
            logger.warning(f"User not found: user_id={user_id}")
            raise HTTPException(status_code=404, detail="User not found")

        if not profile:
            logger.warning(f"Profile not found: user_id={user_id}")
            raise HTTPException(status_code=404, detail="Client profile not found")

        fields = update.model_dump(exclude_unset=True)

        # Update User model fields
        for attr in ["first_name", "last_name", "location", "profile_picture"]:
            if attr in fields:
                setattr(user, attr, fields[attr])
                logger.debug(f"Updated User.{attr} = {fields[attr]}")

        # Update ClientProfile model fields
        for attr in ["business_name"]:
            if attr in fields:
                setattr(profile, attr, fields[attr])
                logger.debug(f"Updated ClientProfile.{attr} = {fields[attr]}")

        await self.db.commit()
        await self.db.refresh(user)
        await self.db.refresh(profile)

        logger.info(f"Profile updated for user_id={user_id}, profile_id={profile.id}")

        merged = {
            **{k: v for k, v in vars(profile).items() if not k.startswith("_")},
            **{k: v for k, v in vars(user).items() if not k.startswith("_")}
        }
        return schemas.ClientProfileRead.model_validate(merged)

    # -------------------------------
    # Favorites Management
    # -------------------------------

    async def list_favorites(self, client_id: UUID):
        """
        Retrieve all favorite workers saved by the client.
        """
        logger.info(f"Listing favorites for client_id={client_id}")
        return (await self.db.execute(
            select(models.FavoriteWorker).filter(models.FavoriteWorker.client_id == client_id))
        ).scalars().all()

    async def add_favorite(self, client_id: UUID, worker_id: UUID) -> models.FavoriteWorker:
        """
        Add a worker to the client's list of favorites.
        """
        logger.info(f"Adding favorite: client_id={client_id}, worker_id={worker_id}")

        existing = (await self.db.execute(
            select(models.FavoriteWorker).filter(
                models.FavoriteWorker.client_id == client_id,
                models.FavoriteWorker.worker_id == worker_id
            ))
        ).scalar_one_or_none()

        if existing:
            logger.warning("Worker already favorited")
            raise HTTPException(status_code=400, detail="Worker already in favorites")

        favorite = models.FavoriteWorker(client_id=client_id, worker_id=worker_id)
        self.db.add(favorite)
        await self.db.commit()
        await self.db.refresh(favorite)

        logger.info(f"Favorite added: favorite_id={favorite.id}")
        return favorite

    async def remove_favorite(self, client_id: UUID, worker_id: UUID):
        """
        Remove a worker from the client's favorites list.
        """
        logger.info(f"Removing favorite: client_id={client_id}, worker_id={worker_id}")

        favorite = (await self.db.execute(
            select(models.FavoriteWorker).filter(
                models.FavoriteWorker.client_id == client_id,
                models.FavoriteWorker.worker_id == worker_id
            ))
        ).scalar_one_or_none()

        if not favorite:
            logger.warning("Favorite not found")
            raise HTTPException(status_code=404, detail="Favorite not found")

        self.db.delete(favorite)
        await self.db.commit()

        logger.info("Favorite removed successfully")

    # -------------------------------
    # Job History
    # -------------------------------

    async def get_jobs(self, client_id: UUID):
        """
        Retrieve all jobs created by the client.
        """
        logger.info(f"Fetching job list for client_id={client_id}")
        return (await self.db.execute(
            select(Job).filter(Job.client_id == client_id))
        ).scalars().all()

    async def get_job_detail(self, client_id: UUID, job_id: UUID):
        """
        Retrieve detailed info about a job created by the client.
        """
        logger.info(f"Fetching job detail: client_id={client_id}, job_id={job_id}")

        job = (await self.db.execute(
            select(Job).filter(
                Job.id == job_id,
                Job.client_id == client_id
            ))
        ).scalar_one_or_none()

        if not job:
            logger.warning("Job not found or unauthorized access")
            raise HTTPException(status_code=404, detail="Job not found or unauthorized")

        logger.info(f"Job retrieved: job_id={job.id}")
        return job
