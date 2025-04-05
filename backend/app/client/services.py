"""
client/services.py

Service class for handling all client-related logic, including:
- Client profile management
- Favorite worker management
- Job history retrieval
"""

import logging
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

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

    # ---------------------------
    # Client Profile Services
    # ---------------------------

    def get_profile(self, user_id: UUID) -> models.ClientProfile:
        """
        Retrieves the client profile for a given user ID.
        """
        logger.info(f"Retrieving client profile for user_id={user_id}")
        profile = self.db.query(models.ClientProfile).filter_by(user_id=user_id).first()

        if not profile:
            logger.warning(f"Client profile not found for user_id={user_id}")
            raise HTTPException(status_code=404, detail="Client profile not found")

        logger.info(f"Client profile retrieved: profile_id={profile.id}")
        return profile

    def update_profile(self, user_id: UUID, data: schemas.ClientProfileUpdate) -> models.ClientProfile:
        """
        Updates the client profile for a given user ID using provided data.
        """
        logger.info(f"Updating client profile for user_id={user_id}")
        profile = self.get_profile(user_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(profile, field, value)
            logger.debug(f"Updated field '{field}' to '{value}'")

        self.db.commit()
        self.db.refresh(profile)

        logger.info(f"Client profile updated: profile_id={profile.id}")
        return profile

    # ---------------------------
    # Favorite Worker Services
    # ---------------------------

    def list_favorites(self, client_id: UUID):
        """
        Returns a list of favorite workers for a given client.
        """
        logger.info(f"Listing favorites for client_id={client_id}")
        return self.db.query(models.FavoriteWorker).filter_by(client_id=client_id).all()

    def add_favorite(self, client_id: UUID, worker_id: UUID) -> models.FavoriteWorker:
        """
        Adds a worker to the client's favorites list.
        """
        logger.info(f"Adding favorite: client_id={client_id}, worker_id={worker_id}")

        existing = self.db.query(models.FavoriteWorker).filter_by(
            client_id=client_id,
            worker_id=worker_id
        ).first()

        if existing:
            logger.warning("Worker already in favorites.")
            raise HTTPException(status_code=400, detail="Worker already in favorites")

        favorite = models.FavoriteWorker(client_id=client_id, worker_id=worker_id)
        self.db.add(favorite)
        self.db.commit()
        self.db.refresh(favorite)

        logger.info(f"Favorite added: favorite_id={favorite.id}")
        return favorite

    def remove_favorite(self, client_id: UUID, worker_id: UUID):
        """
        Removes a worker from the client's favorites list.
        """
        logger.info(f"Removing favorite: client_id={client_id}, worker_id={worker_id}")

        favorite = self.db.query(models.FavoriteWorker).filter_by(
            client_id=client_id,
            worker_id=worker_id
        ).first()

        if not favorite:
            logger.warning("Favorite not found.")
            raise HTTPException(status_code=404, detail="Favorite not found")

        self.db.delete(favorite)
        self.db.commit()

        logger.info("Favorite removed successfully.")
        return

    # ---------------------------
    # Job History Services
    # ---------------------------

    def get_jobs(self, client_id: UUID):
        """
        Retrieves all jobs associated with the client.
        """
        logger.info(f"Fetching job history for client_id={client_id}")
        return self.db.query(Job).filter_by(client_id=client_id).all()

    def get_job_detail(self, client_id: UUID, job_id: UUID):
        """
        Retrieves a single job by ID, ensuring it belongs to the client.
        """
        logger.info(f"Fetching job detail: job_id={job_id}, client_id={client_id}")
        job = self.db.query(Job).filter_by(id=job_id, client_id=client_id).first()

        if not job:
            logger.warning("Job not found or unauthorized access.")
            raise HTTPException(status_code=404, detail="Job not found or unauthorized")

        logger.info(f"Job detail retrieved: job_id={job.id}")
        return job
