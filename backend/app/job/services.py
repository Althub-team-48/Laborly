"""
job/services.py

Encapsulates all business logic for managing job lifecycle:
- Accepting, completing, and cancelling jobs
- Fetching job history and specific job details
"""

import logging
from uuid import UUID
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.job import models, schemas
from app.job.models import JobStatus
from app.messaging.models import MessageThread
from app.service.models import Service

logger = logging.getLogger(__name__)


class JobService:
    """
    Service class for job-related actions including accept, complete, cancel,
    fetch job list and details. Acts as the business logic layer.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_job(self, client_id: UUID, payload: schemas.JobCreate) -> models.Job:
        """
        Client initiates a new job request with a specific worker, service, and conversation thread.
        The job status is set to 'NEGOTIATING' while waiting for the worker to accept it.
        """
        logger.info(
            f"[CREATE] Client {client_id} creating job with service {payload.service_id} via thread {payload.thread_id}"
        )

        service = (
            (await self.db.execute(select(Service).filter_by(id=payload.service_id)))
            .unique()
            .scalar_one_or_none()
        )
        if not service:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Service with ID {payload.service_id} does not exist.",
            )

        worker_id = service.worker_id

        thread = (
            (await self.db.execute(select(MessageThread).filter_by(id=payload.thread_id)))
            .unique()
            .scalar_one_or_none()
        )
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Message thread with ID {payload.thread_id} does not exist.",
            )

        job = models.Job(
            client_id=client_id,
            worker_id=worker_id,
            service_id=payload.service_id,
            status=JobStatus.NEGOTIATING,
            thread_id=payload.thread_id,
            started_at=None,
        )

        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)

        logger.info(f"[CREATE] Job created: job_id={job.id}")
        return job

    async def accept_job(self, payload: schemas.JobAccept) -> models.Job:
        """
        Worker accepts the job. The job status is updated to 'ACCEPTED'.
        """
        logger.info(f"[ACCEPT] Worker {payload.worker_id} accepting job {payload.job_id}")

        job = (
            (await self.db.execute(select(models.Job).filter_by(id=payload.job_id)))
            .unique()
            .scalar_one_or_none()
        )
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status != JobStatus.NEGOTIATING:
            raise HTTPException(
                status_code=400, detail="Only jobs in 'NEGOTIATING' status can be accepted"
            )

        job.status = JobStatus.ACCEPTED
        job.started_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(job)

        logger.info(f"[ACCEPT] Job accepted: job_id={job.id}")
        return job

    async def complete_job(self, user_id: UUID, job_id: UUID) -> models.Job:
        """
        Marks an accepted job as completed.
        """
        logger.info(f"[COMPLETE] User {user_id} attempting to complete job {job_id}")

        job = (
            (await self.db.execute(select(models.Job).filter_by(id=job_id)))
            .unique()
            .scalar_one_or_none()
        )
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status != JobStatus.ACCEPTED:
            raise HTTPException(
                status_code=400, detail="Only accepted jobs can be marked as completed"
            )

        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(job)

        logger.info(f"[COMPLETE] Job marked completed: job_id={job.id}")
        return job

    async def cancel_job(self, user_id: UUID, job_id: UUID, cancel_reason: str) -> models.Job:
        """
        Cancels an ongoing job and records the cancellation reason.
        """
        logger.info(f"[CANCEL] User {user_id} attempting to cancel job {job_id}")

        job = (
            (await self.db.execute(select(models.Job).filter_by(id=job_id)))
            .unique()
            .scalar_one_or_none()
        )
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status in {JobStatus.COMPLETED, JobStatus.CANCELLED}:
            raise HTTPException(status_code=400, detail="This job cannot be cancelled")

        job.status = JobStatus.CANCELLED
        job.cancelled_at = datetime.now(timezone.utc)
        job.cancel_reason = cancel_reason

        await self.db.commit()
        await self.db.refresh(job)

        logger.info(f"[CANCEL] Job cancelled: job_id={job.id}")
        return job

    async def get_all_jobs_for_user(self, user_id: UUID) -> list[models.Job]:
        """
        Returns all jobs where the user is either a client or worker.
        """
        logger.info(f"[FETCH] Retrieving job list for user_id={user_id}")

        result = await self.db.execute(
            select(models.Job).filter(
                (models.Job.client_id == user_id) | (models.Job.worker_id == user_id)
            )
        )
        jobs = result.scalars().all()

        logger.info(f"[FETCH] {len(jobs)} jobs found for user_id={user_id}")
        return list(jobs)

    async def get_job_detail(self, user_id: UUID, job_id: UUID) -> models.Job:
        """
        Retrieves detailed information about a specific job, ensuring user has access.
        """
        logger.info(f"[DETAIL] Fetching job {job_id} for user_id={user_id}")

        job = (
            (await self.db.execute(select(models.Job).filter_by(id=job_id)))
            .unique()
            .scalar_one_or_none()
        )
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if user_id not in {job.client_id, job.worker_id}:
            raise HTTPException(
                status_code=403, detail="You do not have permission to access this job"
            )

        logger.info(f"[DETAIL] Job retrieved: job_id={job.id}")
        return job
