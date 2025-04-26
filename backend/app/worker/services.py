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

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.upload import generate_presigned_url, get_s3_key_from_url
from app.database.enums import KYCStatus
from app.worker import models, schemas
from app.database.models import User, KYC
from app.job.models import Job

logger = logging.getLogger(__name__)


class WorkerService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_profile_picture_presigned_url(self, user_id: UUID) -> str | None:
        """
        Gets the user's profile picture S3 URL and returns a pre-signed URL for it.

        Returns:
            Optional[str]: The pre-signed URL or None if no picture is set or generation fails.
        """
        logger.info(f"Requesting pre-signed URL for profile picture of worker user_id={user_id}")
        user = await self._get_user_or_404(user_id)

        s3_full_url = user.profile_picture
        if not s3_full_url:
            logger.info(f"Worker {user_id} does not have a profile picture set.")
            return None

        s3_key = get_s3_key_from_url(s3_full_url)
        if not s3_key:
            logger.error(
                f"Could not extract S3 key from stored profile picture URL for worker {user_id}: {s3_full_url}"
            )
            return None

        presigned_url = generate_presigned_url(s3_key, expiration=3600)
        if not presigned_url:
            logger.error(
                f"Failed to generate pre-signed URL for worker profile picture key: {s3_key}"
            )
            return None

        return presigned_url

    async def _get_user_and_profile(self, user_id: UUID) -> tuple[User, models.WorkerProfile]:
        """Fetches user and their worker profile, creating profile if needed."""
        user = await self._get_user_or_404(user_id)

        profile = (
            (await self.db.execute(select(models.WorkerProfile).filter_by(user_id=user_id)))
            .unique()
            .scalar_one_or_none()
        )

        if not profile:
            logger.info(f"No profile found. Creating new worker profile for user_id={user_id}")
            profile = models.WorkerProfile(user_id=user_id)
            self.db.add(profile)
            await self.db.flush()
            await self.db.refresh(profile)
            logger.info(f"New worker profile created: profile_id={profile.id}")

        return user, profile

    async def _get_user_or_404(self, user_id: UUID) -> User:
        """Helper method to retrieve a user or raise 404 if not found."""
        user = await self.db.get(User, user_id)
        if not user:
            logger.warning(f"[UTIL] User not found: user_id={user_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    # ---------------------------------------------
    # Worker Profile Methods
    # ---------------------------------------------
    async def get_profile(self, user_id: UUID) -> schemas.WorkerProfileRead:
        """Retrieve or create a worker profile."""
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
        """Update worker profile fields (excluding picture)."""
        logger.info(f"Updating worker profile for user_id={user_id}")
        user, profile = await self._get_user_and_profile(user_id)

        update_data = data.model_dump(exclude_unset=True)

        user_fields = {"first_name", "last_name", "phone_number", "location"}
        user_updated = False
        for field in user_fields.intersection(update_data.keys()):
            setattr(user, field, update_data[field])
            user_updated = True
            logger.debug(f"Updated user.{field} = {update_data[field]}")

        profile_fields = {
            "bio",
            "years_experience",
            "availability_note",
            "is_available",
            "professional_skills",
            "work_experience",
        }
        profile_updated = False
        for field in profile_fields.intersection(update_data.keys()):
            setattr(profile, field, update_data[field])
            profile_updated = True
            logger.debug(f"Updated profile.{field} = {update_data[field]}")

        if not user_updated and not profile_updated:
            logger.info(f"No fields to update for worker profile user_id={user_id}")
            merged_data = {
                "user_id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone_number": user.phone_number,
                "location": user.location,
                "profile_picture": user.profile_picture,
                "bio": profile.bio,
                "years_experience": profile.years_experience,
                "availability_note": profile.availability_note,
                "is_available": profile.is_available,
                "professional_skills": profile.professional_skills,
                "work_experience": profile.work_experience,
            }
            return schemas.WorkerProfileRead.model_validate(merged_data)

        try:
            await self.db.commit()
            if user_updated:
                await self.db.refresh(user)
            if profile_updated:
                await self.db.refresh(profile)
        except Exception as e:
            logger.error(
                f"Error committing worker profile update for {user_id}: {e}", exc_info=True
            )
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
        """
        Updates only the profile picture URL on the User model for a worker.
        """
        logger.info(f"Updating worker profile picture for user_id={user_id} to {picture_url}")
        user, profile = await self._get_user_and_profile(user_id)

        if user.profile_picture == picture_url:
            logger.info(f"Profile picture for worker {user_id} is already set to the provided URL.")
        else:
            user.profile_picture = picture_url
            try:
                await self.db.commit()
                await self.db.refresh(user)
            except Exception as e:
                logger.error(
                    f"Error committing worker profile picture update for user {user_id}: {e}",
                    exc_info=True,
                )
                await self.db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update profile picture.",
                )
        return schemas.MessageResponse(detail="Profile picture updated successfully.")

    async def toggle_availability(self, user_id: UUID, status: bool) -> models.WorkerProfile:
        logger.info(f"Toggling availability: user_id={user_id}, status={status}")
        profile = (
            (await self.db.execute(select(models.WorkerProfile).filter_by(user_id=user_id)))
            .unique()
            .scalar_one_or_none()
        )
        if not profile:
            await self._get_user_or_404(user_id)
            profile = models.WorkerProfile(user_id=user_id, is_available=status)
            self.db.add(profile)
            logger.info(f"Created worker profile for user {user_id} while toggling availability.")
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
        logger.info(f"Submitting KYC for user_id={user_id}")
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
        logger.info(f"KYC submitted/updated: user_id={user_id}, kyc_id={kyc.id}")
        return kyc

    # ---------------------------------------------
    # Job Management Methods
    # ---------------------------------------------
    async def get_jobs(self, user_id: UUID) -> list[Job]:
        logger.info(f"Fetching jobs for worker user_id={user_id}")
        result = await self.db.execute(
            select(Job).filter_by(worker_id=user_id).order_by(Job.created_at.desc())
        )
        jobs = list(result.unique().scalars().all())
        logger.info(f"Found {len(jobs)} jobs for worker {user_id}")
        return jobs

    async def get_job_detail(self, user_id: UUID, job_id: UUID) -> Job:
        logger.info(f"Fetching job_id={job_id} detail for worker user_id={user_id}")
        stmt = select(Job).filter_by(id=job_id, worker_id=user_id)
        # stmt = stmt.options(selectinload(Job.client), selectinload(Job.service))
        job = (await self.db.execute(stmt)).unique().scalar_one_or_none()

        if not job:
            logger.warning(f"Job {job_id} not found or access denied for worker {user_id}")
            raise HTTPException(status_code=404, detail="Job not found or unauthorized")
        return job
