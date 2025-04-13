"""
worker/services.py

Handles business logic for the Worker module:
- Worker profile and availability
- KYC submission and retrieval
- Assigned job history
"""

import logging
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.worker import models, schemas
from app.database.models import User, KYC
from app.job.models import Job

logger = logging.getLogger(__name__)


class WorkerService:
    """
    Encapsulates business logic for worker-specific functionality.
    """

    def __init__(self, db: Session):
        self.db = db

    # -----------------------------------
    # Worker Profile Management
    # -----------------------------------

    def get_profile(self, user_id: UUID) -> schemas.WorkerProfileRead:
        """
        Retrieve the merged worker profile and user details for the given user ID.
        Creates a profile if none exists.
        """
        logger.info(f"Fetching worker profile for user_id={user_id}")

        user = self.db.query(User).filter_by(id=user_id).first()
        if not user:
            logger.warning(f"User not found for user_id={user_id}")
            raise HTTPException(status_code=404, detail="User not found")

        profile = self.db.query(models.WorkerProfile).filter_by(user_id=user_id).first()
        if not profile:
            logger.info("No profile found. Creating new worker profile...")
            profile = models.WorkerProfile(user_id=user_id)
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)

        merged_data = {
            **{k: v for k, v in vars(profile).items() if not k.startswith("_")},
            **{k: v for k, v in vars(user).items() if not k.startswith("_")},
        }
        return schemas.WorkerProfileRead.model_validate(merged_data)

    def update_profile(self, user_id: UUID, data: schemas.WorkerProfileUpdate) -> schemas.WorkerProfileRead:
        """
        Update both user and profile fields for the given worker.
        """
        logger.info(f"Updating worker profile for user_id={user_id}")

        user = self.db.query(User).filter_by(id=user_id).first()
        if not user:
            logger.warning(f"User not found for user_id={user_id}")
            raise HTTPException(status_code=404, detail="User not found")

        profile = self.db.query(models.WorkerProfile).filter_by(user_id=user_id).first()
        if not profile:
            logger.warning(f"Profile not found for user_id={user_id}")
            raise HTTPException(status_code=404, detail="Worker profile not found")

        update_data = data.model_dump(exclude_unset=True)

        # Update User model fields
        user_fields = {col.name for col in User.__table__.columns}
        for field in user_fields & update_data.keys():
            setattr(user, field, update_data[field])
            logger.debug(f"Updated user.{field} = {update_data[field]}")

        # Update WorkerProfile model fields
        profile_fields = {col.name for col in models.WorkerProfile.__table__.columns}
        for field in profile_fields & update_data.keys():
            setattr(profile, field, update_data[field])
            logger.debug(f"Updated profile.{field} = {update_data[field]}")

        self.db.commit()
        self.db.refresh(user)
        self.db.refresh(profile)

        merged_data = {
            **{k: v for k, v in vars(profile).items() if not k.startswith("_")},
            **{k: v for k, v in vars(user).items() if not k.startswith("_")},
        }
        return schemas.WorkerProfileRead.model_validate(merged_data)

    # -----------------------------------
    # Availability Management
    # -----------------------------------

    def toggle_availability(self, user_id: UUID, status: bool) -> models.WorkerProfile:
        """
        Update the is_available flag on the worker profile.
        """
        logger.info(f"Toggling availability: user_id={user_id}, status={status}")

        profile = self.db.query(models.WorkerProfile).filter_by(user_id=user_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Worker profile not found")

        profile.is_available = status
        self.db.commit()
        self.db.refresh(profile)

        logger.info(f"Availability updated: user_id={user_id}, status={profile.is_available}")
        return profile

    # -----------------------------------
    # KYC Handling
    # -----------------------------------

    def get_kyc(self, user_id: UUID) -> KYC:
        """
        Retrieve the KYC record for the user.
        """
        logger.info(f"Fetching KYC for user_id={user_id}")

        kyc = self.db.query(KYC).filter_by(user_id=user_id).first()
        if not kyc:
            raise HTTPException(status_code=404, detail="No KYC record found")
        return kyc

    def submit_kyc(self, user_id: UUID, document_type: str, document_path: str, selfie_path: str) -> KYC:
        """
        Create or update a KYC record for the worker.
        """
        logger.info(f"Submitting KYC for user_id={user_id}")

        kyc = self.db.query(KYC).filter_by(user_id=user_id).first()
        now = datetime.now(timezone.utc)

        if not kyc:
            kyc = KYC(
                user_id=user_id,
                document_type=document_type,
                document_path=document_path,
                selfie_path=selfie_path,
                submitted_at=now
            )
            self.db.add(kyc)
        else:
            kyc.document_type = document_type
            kyc.document_path = document_path
            kyc.selfie_path = selfie_path
            kyc.submitted_at = now

        kyc.status = "PENDING"
        self.db.commit()
        self.db.refresh(kyc)

        logger.info(f"KYC submitted: user_id={user_id}, kyc_id={kyc.id}")
        return kyc

    # -----------------------------------
    # Job Management
    # -----------------------------------

    def get_jobs(self, user_id: UUID):
        """
        Return all jobs assigned to the worker.
        """
        logger.info(f"Fetching jobs for user_id={user_id}")
        return self.db.query(Job).filter_by(worker_id=user_id).all()

    def get_job_detail(self, user_id: UUID, job_id: UUID):
        """
        Return a specific job assigned to the worker.
        """
        logger.info(f"Fetching job_id={job_id} for user_id={user_id}")

        job = self.db.query(Job).filter_by(id=job_id, worker_id=user_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found or unauthorized")

        return job
