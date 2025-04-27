"""
backend/app/worker/services.py

Worker Service Layer
Handles core business logic for worker profile management, KYC processing,
profile picture handling, and job history operations.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.upload import generate_presigned_url, get_s3_key_from_url
from app.database.enums import KYCStatus, UserRole
from app.database.models import KYC, User
from app.job.models import Job
from app.worker import models, schemas

logger = logging.getLogger(__name__)


class WorkerService:
    """Service class to handle worker-related operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---------------------------------------------
    # Internal Utility Methods
    # ---------------------------------------------
    async def _get_user_or_404(self, user_id: UUID) -> User:
        """Helper method to retrieve a user or raise 404 if not found."""
        user = await self.db.get(User, user_id)
        if not user:
            logger.warning(f"User not found: user_id={user_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    async def _get_user_and_profile(self, user_id: UUID) -> tuple[User, models.WorkerProfile]:
        """Fetch user and worker profile; create profile if it does not exist."""
        user = await self._get_user_or_404(user_id)

        profile = (
            (await self.db.execute(select(models.WorkerProfile).filter_by(user_id=user_id)))
            .unique()
            .scalar_one_or_none()
        )

        if not profile:
            logger.info(f"Creating new worker profile for user_id={user_id}")
            profile = models.WorkerProfile(user_id=user_id)
            self.db.add(profile)
            await self.db.flush()
            await self.db.refresh(profile)
            logger.info(f"New worker profile created: profile_id={profile.id}")

        return user, profile

    # ---------------------------------------------
    # Worker Profile Methods (Authenticated)
    # ---------------------------------------------
    async def get_profile_picture_presigned_url(self, user_id: UUID) -> str | None:
        """Generate a pre-signed S3 URL for a worker's profile picture."""
        logger.info(f"Requesting pre-signed URL for profile picture: user_id={user_id}")
        user = await self._get_user_or_404(user_id)

        if not user.profile_picture:
            logger.info(f"No profile picture set for worker {user_id}")
            return None

        s3_key = get_s3_key_from_url(user.profile_picture)
        if not s3_key:
            logger.error(f"Failed to extract S3 key from URL for worker {user_id}")
            return None

        presigned_url = generate_presigned_url(s3_key, expiration=3600)
        if not presigned_url:
            logger.error(f"Failed to generate pre-signed URL for key: {s3_key}")
            return None

        return presigned_url

    async def get_profile(self, user_id: UUID) -> schemas.WorkerProfileRead:
        """Retrieve or create the authenticated worker's profile."""
        logger.info(f"Fetching worker profile for user_id={user_id}")
        user, profile = await self._get_user_and_profile(user_id)

        merged_data = {
            **{k: v for k, v in vars(profile).items() if not k.startswith("_")},
            "user_id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone_number": user.phone_number,
            "location": user.location,
            "profile_picture": user.profile_picture,
        }
        return schemas.WorkerProfileRead.model_validate(merged_data)

    async def update_profile(
        self, user_id: UUID, data: schemas.WorkerProfileUpdate
    ) -> schemas.WorkerProfileRead:
        """Update worker profile fields excluding profile picture."""
        logger.info(f"Updating profile for user_id={user_id}")
        user, profile = await self._get_user_and_profile(user_id)

        update_data = data.model_dump(exclude_unset=True)

        user_fields = {"first_name", "last_name", "phone_number", "location"}
        profile_fields = {
            "bio",
            "years_experience",
            "availability_note",
            "is_available",
            "professional_skills",
            "work_experience",
        }

        user_updated = False
        for field in user_fields.intersection(update_data):
            setattr(user, field, update_data[field])
            user_updated = True
            logger.debug(f"Updated user field {field}: {update_data[field]}")

        profile_updated = False
        for field in profile_fields.intersection(update_data):
            setattr(profile, field, update_data[field])
            profile_updated = True
            logger.debug(f"Updated profile field {field}: {update_data[field]}")

        if not user_updated and not profile_updated:
            logger.info(f"No fields to update for user_id={user_id}")
            merged_data = {**vars(profile), **vars(user)}
            return schemas.WorkerProfileRead.model_validate(merged_data, from_attributes=True)

        try:
            await self.db.commit()
            if user_updated:
                await self.db.refresh(user)
            if profile_updated:
                await self.db.refresh(profile)
        except Exception as e:
            logger.error(f"Commit error during profile update for {user_id}: {e}", exc_info=True)
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update profile.",
            )

        merged_data = {
            **{k: v for k, v in vars(profile).items() if not k.startswith("_")},
            "user_id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone_number": user.phone_number,
            "location": user.location,
            "profile_picture": user.profile_picture,
        }
        return schemas.WorkerProfileRead.model_validate(merged_data)

    async def update_profile_picture(
        self, user_id: UUID, picture_url: str
    ) -> schemas.MessageResponse:
        """Update profile picture URL for the worker."""
        logger.info(f"Updating profile picture for user_id={user_id}")
        user, _ = await self._get_user_and_profile(user_id)

        if user.profile_picture != picture_url:
            user.profile_picture = picture_url
            try:
                await self.db.commit()
                await self.db.refresh(user)
            except Exception as e:
                logger.error(f"Error updating profile picture for {user_id}: {e}", exc_info=True)
                await self.db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update profile picture.",
                )
        else:
            logger.info(f"Profile picture already set for user_id={user_id}")

        return schemas.MessageResponse(detail="Profile picture updated successfully.")

    # ---------------------------------------------
    # Worker Profile Methods (Public)
    # ---------------------------------------------
    async def get_public_worker_profile(self, user_id: UUID) -> schemas.PublicWorkerRead:
        """Retrieve public view of a worker profile."""
        logger.info(f"Fetching public profile for user_id={user_id}")
        user = await self.db.get(User, user_id)
        if not user or user.role != UserRole.WORKER:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")

        profile = (
            (await self.db.execute(select(models.WorkerProfile).filter_by(user_id=user_id)))
            .unique()
            .scalar_one_or_none()
        )

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Worker profile not found"
            )

        merged_data = {
            "user_id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "location": user.location,
            "professional_skills": profile.professional_skills,
            "work_experience": profile.work_experience,
            "years_experience": profile.years_experience,
            "bio": profile.bio,
            "is_available": profile.is_available,
            "is_kyc_verified": profile.is_kyc_verified,
        }
        return schemas.PublicWorkerRead.model_validate(merged_data)

    async def toggle_availability(self, user_id: UUID, status: bool) -> models.WorkerProfile:
        """Toggle the availability status for a worker."""
        logger.info(f"Toggling availability for user_id={user_id} to {status}")

        profile = (
            (await self.db.execute(select(models.WorkerProfile).filter_by(user_id=user_id)))
            .unique()
            .scalar_one_or_none()
        )

        if not profile:
            await self._get_user_or_404(user_id)
            profile = models.WorkerProfile(user_id=user_id, is_available=status)
            self.db.add(profile)
            logger.info(f"Created worker profile while toggling availability for {user_id}.")
        else:
            profile.is_available = status

        await self.db.commit()
        await self.db.refresh(profile)
        logger.info(f"Availability updated: user_id={user_id}, status={profile.is_available}")
        return profile

    # ---------------------------------------------
    # KYC Management Methods
    # ---------------------------------------------
    async def get_kyc(self, user_id: UUID) -> KYC | None:
        """Retrieve KYC record for the authenticated worker."""
        logger.info(f"Fetching KYC for user_id={user_id}")
        kyc = (
            (await self.db.execute(select(KYC).filter_by(user_id=user_id)))
            .unique()
            .scalar_one_or_none()
        )
        return kyc

    async def submit_kyc(
        self, user_id: UUID, document_type: str, document_path: str, selfie_path: str
    ) -> KYC:
        """Submit or update KYC documents for a worker."""
        logger.info(f"Submitting KYC documents for user_id={user_id}")

        kyc = (
            (await self.db.execute(select(KYC).filter_by(user_id=user_id)))
            .unique()
            .scalar_one_or_none()
        )
        now = datetime.now(timezone.utc)

        if not kyc:
            kyc = KYC(
                user_id=user_id,
                document_type=document_type,
                document_path=document_path,
                selfie_path=selfie_path,
                submitted_at=now,
                status=KYCStatus.PENDING,
            )
            self.db.add(kyc)
        else:
            kyc.document_type = document_type
            kyc.document_path = document_path
            kyc.selfie_path = selfie_path
            kyc.submitted_at = now
            kyc.status = KYCStatus.PENDING
            kyc.reviewed_at = None

        await self.db.commit()
        await self.db.refresh(kyc)
        logger.info(f"KYC record submitted/updated for user_id={user_id}")
        return kyc

    # ---------------------------------------------
    # Job Management Methods (Authenticated Worker)
    # ---------------------------------------------
    async def get_jobs(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[Job], int]:
        """Retrieve list of jobs assigned to a worker with pagination and total count."""
        logger.info(f"Fetching jobs for user_id={user_id}")

        # Count total records
        count_stmt = select(func.count()).filter(Job.worker_id == user_id)
        total_count_result = await self.db.execute(count_stmt)
        total_count = total_count_result.scalar_one()

        # Fetch paginated records
        result = await self.db.execute(
            select(Job)
            .filter_by(worker_id=user_id)
            .order_by(Job.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        jobs = list(result.unique().scalars().all())
        logger.info(f"Found {len(jobs)} jobs for user_id={user_id} (Total: {total_count}).")
        return jobs, total_count

    async def get_job_detail(self, user_id: UUID, job_id: UUID) -> Job:
        """Retrieve detailed information for a specific job assigned to a worker."""
        logger.info(f"Fetching job_id={job_id} for worker user_id={user_id}")
        stmt = select(Job).filter_by(id=job_id, worker_id=user_id)
        job = (await self.db.execute(stmt)).unique().scalar_one_or_none()

        if not job:
            logger.warning(f"Job {job_id} not found or access denied for worker {user_id}")
            raise HTTPException(status_code=404, detail="Job not found or unauthorized")
        return job
