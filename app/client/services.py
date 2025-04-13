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
from sqlalchemy.orm import Session

from app.client import models, schemas
from app.database.models import User
from app.job.models import Job

logger = logging.getLogger(__name__)


class ClientService:
    """
    Encapsulates all business logic for the Client module.
    """

    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------
    # Client Profile Management
    # -------------------------------------------

    def get_profile(self, user_id: UUID) -> schemas.ClientProfileRead:
        """
        Retrieve the client profile and merge user account data.
        Creates a new profile automatically if one does not exist.
        """
        logger.info(f"Retrieving client profile for user_id={user_id}")

        user = self.db.query(User).filter_by(id=user_id).first()
        if not user:
            logger.warning(f"User not found: user_id={user_id}")
            raise HTTPException(status_code=404, detail="User not found")

        profile = self.db.query(models.ClientProfile).filter_by(user_id=user_id).first()
        if not profile:
            logger.info(f"No profile found. Creating new one for user_id={user_id}")
            profile = models.ClientProfile(user_id=user_id)
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
            logger.info(f"New profile created: profile_id={profile.id}")

        # Merge profile and user data for output
        merged = {
            **{k: v for k, v in vars(profile).items() if not k.startswith("_")},
            **{k: v for k, v in vars(user).items() if not k.startswith("_")},
        }
        return schemas.ClientProfileRead.model_validate(merged)

    def update_profile(self, user_id: UUID, update: schemas.ClientProfileUpdate) -> schemas.ClientProfileRead:
        """
        Update both user and profile details for the given client.
        """
        logger.info(f"Updating profile for user_id={user_id}")

        user = self.db.query(User).filter_by(id=user_id).first()
        profile = self.db.query(models.ClientProfile).filter_by(user_id=user_id).first()

        if not user:
            logger.warning(f"User not found: user_id={user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        if not profile:
            logger.warning(f"Profile not found: user_id={user_id}")
            raise HTTPException(status_code=404, detail="Client profile not found")

        fields = update.model_dump(exclude_unset=True)

        # Update user attributes
        for attr in ["first_name", "last_name", "location", "profile_picture"]:
            if attr in fields:
                setattr(user, attr, fields[attr])
                logger.debug(f"Updated User.{attr} = {fields[attr]}")

        # Update profile-specific attributes
        for attr in ["business_name"]:
            if attr in fields:
                setattr(profile, attr, fields[attr])
                logger.debug(f"Updated ClientProfile.{attr} = {fields[attr]}")

        self.db.commit()
        self.db.refresh(user)
        self.db.refresh(profile)

        logger.info(f"Profile updated for user_id={user_id}, profile_id={profile.id}")

        merged = {
            **{k: v for k, v in vars(profile).items() if not k.startswith("_")},
            **{k: v for k, v in vars(user).items() if not k.startswith("_")},
        }
        return schemas.ClientProfileRead.model_validate(merged)

    # -------------------------------------------
    # Favorite Worker Management
    # -------------------------------------------

    def list_favorites(self, client_id: UUID):
        """
        List all favorite workers for a given client.
        """
        logger.info(f"Listing favorites for client_id={client_id}")
        return self.db.query(models.FavoriteWorker).filter_by(client_id=client_id).all()

    def add_favorite(self, client_id: UUID, worker_id: UUID) -> models.FavoriteWorker:
        """
        Add a worker to the client's list of favorites.
        """
        logger.info(f"Adding favorite: client_id={client_id}, worker_id={worker_id}")

        existing = self.db.query(models.FavoriteWorker).filter_by(
            client_id=client_id,
            worker_id=worker_id
        ).first()

        if existing:
            logger.warning("Worker already favorited")
            raise HTTPException(status_code=400, detail="Worker already in favorites")

        favorite = models.FavoriteWorker(client_id=client_id, worker_id=worker_id)
        self.db.add(favorite)
        self.db.commit()
        self.db.refresh(favorite)

        logger.info(f"Favorite added: favorite_id={favorite.id}")
        return favorite

    def remove_favorite(self, client_id: UUID, worker_id: UUID):
        """
        Remove a worker from the client's favorites list.
        """
        logger.info(f"Removing favorite: client_id={client_id}, worker_id={worker_id}")

        favorite = self.db.query(models.FavoriteWorker).filter_by(
            client_id=client_id,
            worker_id=worker_id
        ).first()

        if not favorite:
            logger.warning("Favorite not found")
            raise HTTPException(status_code=404, detail="Favorite not found")

        self.db.delete(favorite)
        self.db.commit()
        logger.info("Favorite removed successfully")

    # -------------------------------------------
    # Job History Management
    # -------------------------------------------

    def get_jobs(self, client_id: UUID):
        """
        Retrieve all jobs submitted by the client.
        """
        logger.info(f"Fetching job list for client_id={client_id}")
        return self.db.query(Job).filter_by(client_id=client_id).all()

    def get_job_detail(self, client_id: UUID, job_id: UUID):
        """
        Retrieve a specific job record by the client.
        """
        logger.info(f"Fetching job detail: client_id={client_id}, job_id={job_id}")

        job = self.db.query(Job).filter_by(id=job_id, client_id=client_id).first()

        if not job:
            logger.warning("Job not found or unauthorized access")
            raise HTTPException(status_code=404, detail="Job not found or unauthorized")

        logger.info(f"Job retrieved: job_id={job.id}")
        return job
