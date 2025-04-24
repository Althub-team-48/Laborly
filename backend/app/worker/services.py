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

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.enums import KYCStatus
from app.worker import models, schemas
from app.database.models import User, KYC
from app.job.models import Job
from app.job.schemas import JobRead

logger = logging.getLogger(__name__)


class WorkerService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---------------------------------------------
    # Worker Profile Methods
    # ---------------------------------------------

    async def get_profile(self, user_id: UUID) -> schemas.WorkerProfileRead:
        logger.info(f"Fetching worker profile for user_id={user_id}")
        user = (
            (await self.db.execute(select(User).filter_by(id=user_id)))
            .unique()
            .scalar_one_or_none()
        )
        if not user:
            logger.warning(f"User not found for user_id={user_id}")
            raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found.")

        profile = (
            (await self.db.execute(select(models.WorkerProfile).filter_by(user_id=user_id)))
            .unique()
            .scalar_one_or_none()
        )
        if not profile:
            logger.info("No profile found. Creating new worker profile...")
            profile = models.WorkerProfile(user_id=user_id)
            self.db.add(profile)
            await self.db.commit()
            await self.db.refresh(profile)

        merged_data = {
            **{k: v for k, v in vars(profile).items() if not k.startswith("_")},
            **{k: v for k, v in vars(user).items() if not k.startswith("_")},
        }
        return schemas.WorkerProfileRead.model_validate(merged_data)

    async def update_profile(
        self, user_id: UUID, data: schemas.WorkerProfileUpdate
    ) -> schemas.WorkerProfileRead:
        logger.info(f"Updating worker profile for user_id={user_id}")
        user = (
            (await self.db.execute(select(User).filter_by(id=user_id)))
            .unique()
            .scalar_one_or_none()
        )
        if not user:
            logger.warning(f"User not found for user_id={user_id}")
            raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found.")

        profile = (
            (await self.db.execute(select(models.WorkerProfile).filter_by(user_id=user_id)))
            .unique()
            .scalar_one_or_none()
        )
        if not profile:
            logger.warning(f"Profile not found for user_id={user_id}")
            raise HTTPException(status_code=404, detail="Worker profile not found")

        update_data = data.model_dump(exclude_unset=True)

        user_fields = {col.name for col in User.__table__.columns}
        for field in user_fields & update_data.keys():
            setattr(user, field, update_data[field])
            logger.debug(f"Updated user.{field} = {update_data[field]}")

        profile_fields = {col.name for col in models.WorkerProfile.__table__.columns}
        for field in profile_fields & update_data.keys():
            setattr(profile, field, update_data[field])
            logger.debug(f"Updated profile.{field} = {update_data[field]}")

        await self.db.commit()
        await self.db.refresh(user)
        await self.db.refresh(profile)

        merged_data = {
            **{k: v for k, v in vars(profile).items() if not k.startswith("_")},
            **{k: v for k, v in vars(user).items() if not k.startswith("_")},
        }
        return schemas.WorkerProfileRead.model_validate(merged_data)

    async def toggle_availability(self, user_id: UUID, status: bool) -> models.WorkerProfile:
        logger.info(f"Toggling availability: user_id={user_id}, status={status}")
        profile = (
            (await self.db.execute(select(models.WorkerProfile).filter_by(user_id=user_id)))
            .unique()
            .scalar_one_or_none()
        )
        if not profile:
            raise HTTPException(status_code=404, detail="Worker profile not found")

        profile.is_available = status
        await self.db.commit()
        await self.db.refresh(profile)
        logger.info(f"Availability updated: user_id={user_id}, status={profile.is_available}")
        return profile

    # ---------------------------------------------
    # KYC Management Methods
    # ---------------------------------------------

    async def get_kyc(self, user_id: UUID) -> schemas.KYCRead | None:
        logger.info(f"Fetching KYC for user_id={user_id}")
        kyc = (
            (await self.db.execute(select(KYC).filter_by(user_id=user_id)))
            .unique()
            .scalar_one_or_none()
        )
        if not kyc:
            raise HTTPException(
                status_code=404, detail=f"No KYC record found for user_id={user_id}"
            )
        return schemas.KYCRead.model_validate(kyc)

    async def submit_kyc(
        self, user_id: UUID, document_type: str, document_path: str, selfie_path: str
    ) -> schemas.KYCRead:
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
                status="PENDING",
            )
            self.db.add(kyc)
        else:
            kyc.document_type = document_type
            kyc.document_path = document_path
            kyc.selfie_path = selfie_path
            kyc.submitted_at = now
            kyc.status = KYCStatus.PENDING

        await self.db.commit()
        await self.db.refresh(kyc)
        logger.info(f"KYC submitted: user_id={user_id}, kyc_id={kyc.id}")
        return schemas.KYCRead.model_validate(kyc)

    # ---------------------------------------------
    # Job Management Methods
    # ---------------------------------------------

    async def get_jobs(self, user_id: UUID) -> list[JobRead]:
        logger.info(f"Fetching jobs for user_id={user_id}")
        result = await self.db.execute(select(Job).filter_by(worker_id=user_id))
        jobs = result.scalars().all()
        if not jobs:
            raise HTTPException(
                status_code=404, detail=f"No jobs found for worker with user_id={user_id}"
            )
        return [JobRead.model_validate(job) for job in jobs]

    async def get_job_detail(self, user_id: UUID, job_id: UUID) -> JobRead:
        logger.info(f"Fetching job_id={job_id} for user_id={user_id}")
        job = (
            (await self.db.execute(select(Job).filter_by(id=job_id, worker_id=user_id)))
            .unique()
            .scalar_one_or_none()
        )
        if not job:
            raise HTTPException(status_code=404, detail="Job not found or unauthorized")
        return JobRead.model_validate(job)
