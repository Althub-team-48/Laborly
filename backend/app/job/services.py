"""
job/services.py

Encapsulates all business logic for managing job lifecycle:
- Accepting, completing, and cancelling jobs
- Fetching job history and specific job details
"""

import logging
from uuid import UUID
from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.job import models
from app.job.models import JobStatus

logger = logging.getLogger(__name__)


class JobService:
    """
    Handles operations related to jobs:
    - Accepting and assigning jobs
    - Updating job status
    - Retrieving job data for clients and workers
    """

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------
    # Accept Job
    # ---------------------------------------
    def accept_job(self, client_id: UUID, worker_id: UUID, service_id: UUID) -> models.Job:
        """
        Client assigns a job to a specific worker for a given service.
        """
        logger.info(f"[ACCEPT] Client {client_id} initiating job with worker {worker_id}")

        job = models.Job(
            client_id=client_id,
            worker_id=worker_id,
            service_id=service_id,
            status=JobStatus.ACCEPTED,
            started_at=datetime.now(timezone.utc)
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        logger.info(f"[ACCEPT] Job created: job_id={job.id}")
        return job

    # ---------------------------------------
    # Complete Job
    # ---------------------------------------
    def complete_job(self, user_id: UUID, job_id: UUID) -> models.Job:
        """
        Marks a job as completed by the assigned client.
        """
        logger.info(f"[COMPLETE] User {user_id} attempting to complete job {job_id}")

        job = self.db.query(models.Job).filter_by(id=job_id).first()
        if not job:
            logger.error(f"[COMPLETE] Job not found: job_id={job_id}")
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status != JobStatus.ACCEPTED:
            logger.warning(f"[COMPLETE] Invalid status: job_id={job_id}, current_status={job.status}")
            raise HTTPException(status_code=400, detail="Only accepted jobs can be marked as completed")

        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(job)

        logger.info(f"[COMPLETE] Job marked completed: job_id={job.id}")
        return job

    # ---------------------------------------
    # Cancel Job
    # ---------------------------------------
    def cancel_job(self, user_id: UUID, job_id: UUID, cancel_reason: str) -> models.Job:
        """
        Cancels a job with a reason. Only non-completed/cancelled jobs are valid.
        """
        logger.info(f"[CANCEL] User {user_id} attempting to cancel job {job_id}")

        job = self.db.query(models.Job).filter_by(id=job_id).first()
        if not job:
            logger.error(f"[CANCEL] Job not found: job_id={job_id}")
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status in {JobStatus.COMPLETED, JobStatus.CANCELLED}:
            logger.warning(f"[CANCEL] Invalid cancel: job_id={job_id}, status={job.status}")
            raise HTTPException(status_code=400, detail="This job cannot be cancelled")

        job.status = JobStatus.CANCELLED
        job.cancelled_at = datetime.now(timezone.utc)
        job.cancel_reason = cancel_reason
        self.db.commit()
        self.db.refresh(job)

        logger.info(f"[CANCEL] Job cancelled: job_id={job.id}")
        return job

    # ---------------------------------------
    # List All Jobs for a User
    # ---------------------------------------
    def get_all_jobs_for_user(self, user_id: UUID) -> List[models.Job]:
        """
        Retrieves all jobs where the user is either a client or a worker.
        """
        logger.info(f"[FETCH] Retrieving job list for user_id={user_id}")

        jobs = self.db.query(models.Job).filter(
            (models.Job.client_id == user_id) |
            (models.Job.worker_id == user_id)
        ).all()

        logger.info(f"[FETCH] {len(jobs)} jobs found for user_id={user_id}")
        return jobs

    # ---------------------------------------
    # Retrieve a Specific Job
    # ---------------------------------------
    def get_job_detail(self, user_id: UUID, job_id: UUID) -> models.Job:
        """
        Retrieves a job by ID if the current user is involved.
        """
        logger.info(f"[DETAIL] Fetching job {job_id} for user_id={user_id}")

        job = self.db.query(models.Job).filter_by(id=job_id).first()
        if not job:
            logger.error(f"[DETAIL] Job not found: job_id={job_id}")
            raise HTTPException(status_code=404, detail="Job not found")

        if user_id not in {job.client_id, job.worker_id}:
            logger.warning(f"[DETAIL] Unauthorized access: job_id={job_id}, user_id={user_id}")
            raise HTTPException(status_code=403, detail="You do not have permission to access this job")

        logger.info(f"[DETAIL] Job retrieved: job_id={job.id}")
        return job
