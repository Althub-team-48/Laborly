"""
backend/app/job/services.py

Job Services
Encapsulates business logic for managing the job lifecycle:
- Creating, accepting, completing, and cancelling jobs (Authenticated Clients/Workers)
- Fetching job history and specific job details (Authenticated Clients/Workers)
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from myapp.database.enums import UserRole
from myapp.database.models import User
from myapp.job import models, schemas
from myapp.job.models import JobStatus
from myapp.messaging.models import MessageThread
from myapp.service.models import Service

logger = logging.getLogger(__name__)


class JobService:
    """Service class for job-related business logic."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _get_user_or_404(self, user_id: UUID) -> User:
        """Helper to retrieve a user or raise 404 if not found."""
        user = await self.db.get(User, user_id)
        if not user:
            logger.warning(f"User not found: user_id={user_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    # ---------------------------------------------------
    # Job Creation (Client)
    # ---------------------------------------------------
    async def create_job(self, client_id: UUID, payload: schemas.JobCreate) -> models.Job:
        """Client initiates a new job associated with a service and thread."""
        logger.info(
            f"Client {client_id} creating job for service {payload.service_id} via thread {payload.thread_id}"
        )

        client_user = await self._get_user_or_404(client_id)
        if client_user.role != UserRole.CLIENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Only clients can create jobs."
            )

        service = (
            (await self.db.execute(select(Service).filter_by(id=payload.service_id)))
            .unique()
            .scalar_one_or_none()
        )
        if not service:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Service not found."
            )

        worker_id = service.worker_id

        thread = (
            (await self.db.execute(select(MessageThread).filter_by(id=payload.thread_id)))
            .unique()
            .scalar_one_or_none()
        )
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Message thread not found."
            )

        # --- Removed participant check as it's complex here and better handled in messaging ---
        # participant_ids = {p.user_id for p in thread.participants}
        # if not (client_id in participant_ids and worker_id in participant_ids):
        #     raise HTTPException(
        #         status_code=status.HTTP_400_BAD_REQUEST, detail="Thread participants mismatch."
        #     )

        if thread.job_id:
            # Check if the existing job_id still points to a valid job
            existing_job = await self.db.get(models.Job, thread.job_id)
            if existing_job:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A job is already linked to this thread.",
                )
            else:
                # If job_id exists but job doesn't (e.g., deleted), allow linking a new one
                logger.warning(
                    f"Thread {thread.id} has stale job_id {thread.job_id}. Allowing overwrite."
                )
                thread.job_id = None  # Clear stale link before proceeding

        # --- Create Job WITHOUT thread_id ---
        job = models.Job(
            client_id=client_id,
            worker_id=worker_id,
            service_id=payload.service_id,
            status=JobStatus.NEGOTIATING,
        )

        self.db.add(job)
        # --- Flush to get the job ID ---
        await self.db.flush()
        await self.db.refresh(job)  # Refresh to ensure all attributes are loaded

        # --- Update the thread with the new job's ID ---
        thread.job_id = job.id
        self.db.add(thread)  # Mark thread as dirty for update

        # --- Commit both Job creation and Thread update ---
        try:
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error committing job creation or thread update: {e}", exc_info=True)
            await self.db.rollback()
            # Attempt to clean up the newly created job if commit fails
            try:
                await self.db.delete(job)
                await self.db.commit()
            except Exception as delete_err:
                logger.error(
                    f"Failed to rollback job creation {job.id}: {delete_err}", exc_info=True
                )
            raise HTTPException(status_code=500, detail="Failed to create job or link thread.")

        await self.db.refresh(job)  # Refresh again after successful commit

        logger.info(f"Job created successfully: job_id={job.id}, linked to thread_id={thread.id}")
        return job

    # ---------------------------------------------------
    # Job Acceptance (Worker)
    # ---------------------------------------------------
    async def accept_job(self, worker_id: UUID, job_id: UUID) -> models.Job:
        """Worker accepts an assigned job."""
        logger.info(f"Worker {worker_id} accepting job {job_id}")

        worker_user = await self._get_user_or_404(worker_id)
        if worker_user.role != UserRole.WORKER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Only workers can accept jobs."
            )

        job = (
            (await self.db.execute(select(models.Job).filter_by(id=job_id)))
            .unique()
            .scalar_one_or_none()
        )
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.worker_id != worker_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="This job is not assigned to you."
            )

        if job.status != JobStatus.NEGOTIATING:
            raise HTTPException(status_code=400, detail="Only negotiating jobs can be accepted.")

        job.status = JobStatus.ACCEPTED
        job.started_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(job)

        logger.info(f"Job accepted successfully: job_id={job.id}")
        return job

    # ---------------------------------------------------
    # Job Rejection (Worker)
    # ---------------------------------------------------
    async def reject_job(
        self, worker_id: UUID, job_id: UUID, payload: schemas.JobReject
    ) -> models.Job:
        """Worker rejects an assigned job offer."""
        logger.info(f"Worker {worker_id} rejecting job {job_id}")

        worker_user = await self._get_user_or_404(worker_id)
        if worker_user.role != UserRole.WORKER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Only workers can reject jobs."
            )

        stmt = (
            select(models.Job)
            .options(selectinload(models.Job.thread))
            .filter(models.Job.id == job_id)
        )
        result = await self.db.execute(stmt)
        job = result.unique().scalar_one_or_none()

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.worker_id != worker_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="This job is not assigned to you."
            )

        if job.status != JobStatus.NEGOTIATING:
            raise HTTPException(
                status_code=400,
                detail=f"Only jobs in NEGOTIATING status can be rejected. Current status: {job.status}",
            )

        job.status = JobStatus.REJECTED
        job.cancelled_at = datetime.now(timezone.utc)
        job.cancel_reason = payload.reject_reason

        if job.thread:
            job.thread.is_closed = True
            self.db.add(job.thread)
            logger.info(f"Closing thread {job.thread.id} due to job {job.id} rejection.")

        await self.db.commit()
        await self.db.refresh(job)

        if job.thread:
            await self.db.refresh(job.thread)

        logger.info(f"Job rejected successfully: job_id={job.id}")
        return job

    # ---------------------------------------------------
    # Job Completion (Worker)
    # ---------------------------------------------------
    async def complete_job(self, worker_id: UUID, job_id: UUID) -> models.Job:
        """Worker marks an accepted job as completed."""
        logger.info(f"Worker {worker_id} completing job {job_id}")

        worker_user = await self._get_user_or_404(worker_id)
        if worker_user.role != UserRole.WORKER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Only workers can complete jobs."
            )

        job = (
            (await self.db.execute(select(models.Job).filter_by(id=job_id)))
            .unique()
            .scalar_one_or_none()
        )
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.worker_id != worker_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="This job is not assigned to you."
            )

        if job.status != JobStatus.ACCEPTED:
            raise HTTPException(status_code=400, detail="Only accepted jobs can be completed.")

        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(job)

        logger.info(f"Job marked as completed: job_id={job.id}")
        return job

    # ---------------------------------------------------
    # Job Cancellation (Client)
    # ---------------------------------------------------
    async def cancel_job(self, user_id: UUID, job_id: UUID, cancel_reason: str) -> models.Job:
        """Client cancels a job and records a cancellation reason."""
        logger.info(f"Client {user_id} cancelling job {job_id}")

        user = await self._get_user_or_404(user_id)
        if user.role != UserRole.CLIENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Only clients can cancel jobs."
            )

        job = (
            (await self.db.execute(select(models.Job).filter_by(id=job_id)))
            .unique()
            .scalar_one_or_none()
        )
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.client_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="This job does not belong to you."
            )

        if job.status in {JobStatus.COMPLETED, JobStatus.FINALIZED}:
            raise HTTPException(status_code=400, detail="Completed job cannot be cancelled.")

        if job.status == JobStatus.CANCELLED:
            raise HTTPException(status_code=400, detail="This job has been cancelled already.")

        job.status = JobStatus.CANCELLED
        job.cancelled_at = datetime.now(timezone.utc)
        job.cancel_reason = cancel_reason

        await self.db.commit()
        await self.db.refresh(job)

        logger.info(f"Job cancelled successfully: job_id={job.id}")
        return job

    # ---------------------------------------------------
    # Job Retrieval (Client/Worker)
    # ---------------------------------------------------
    async def get_all_jobs_for_user(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[models.Job], int]:
        """Returns all jobs where the user is a client or worker with pagination and total count."""
        logger.info(f"Fetching job list for user_id={user_id}")

        # Count total records
        count_stmt = select(func.count()).filter(
            (models.Job.client_id == user_id) | (models.Job.worker_id == user_id)
        )
        total_count_result = await self.db.execute(count_stmt)
        total_count = total_count_result.scalar_one()

        # Fetch paginated records
        result = await self.db.execute(
            select(models.Job)
            .filter((models.Job.client_id == user_id) | (models.Job.worker_id == user_id))
            .order_by(models.Job.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        jobs = result.scalars().all()

        logger.info(f"Found {len(jobs)} job(s) for user_id={user_id} (Total: {total_count}).")
        return list(jobs), total_count

    async def get_job_detail(self, user_id: UUID, job_id: UUID) -> models.Job:
        """Retrieve detailed information about a specific job for an authenticated user."""
        logger.info(f"Fetching detail for job {job_id} and user_id={user_id}")

        job = (
            (await self.db.execute(select(models.Job).filter_by(id=job_id)))
            .unique()
            .scalar_one_or_none()
        )
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if user_id not in {job.client_id, job.worker_id}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to view this job."
            )

        logger.info(f"Job detail retrieved: job_id={job.id}")
        return job
