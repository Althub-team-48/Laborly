"""
services.py

Handles all job-related business logic, including:
- Accepting a job
- Completing or cancelling a job
- Retrieving job history and details
"""

import logging
from uuid import UUID
from datetime import datetime, timezone
from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.job import models, schemas
from app.job.models import JobStatus

logger = logging.getLogger(__name__)


class JobService:
    """
    Business logic for job creation, updates, and retrieval.
    """

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------
    # Accept Job
    # ---------------------------------------
    def accept_job(self, client_id: UUID, worker_id: UUID, service_id: UUID) -> models.Job:
        logger.info(f"Client {client_id} attempting to assign job to worker {worker_id}")
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
        logger.info(f"Job accepted: job_id={job.id}")
        return job

    # ---------------------------------------
    # Complete Job
    # ---------------------------------------
    def complete_job(self, user_id: UUID, job_id: UUID) -> models.Job:
        logger.info(f"User {user_id} attempting to complete job {job_id}")
        job = self.db.query(models.Job).filter_by(id=job_id).first()

        if not job:
            logger.error(f"Job not found: job_id={job_id}")
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status != JobStatus.ACCEPTED:
            logger.warning(f"Invalid completion status: job_id={job_id}, status={job.status}")
            raise HTTPException(status_code=400, detail="Only accepted jobs can be completed")

        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(job)
        logger.info(f"Job completed: job_id={job.id}")
        return job

    # ---------------------------------------
    # Cancel Job
    # ---------------------------------------
    def cancel_job(self, user_id: UUID, job_id: UUID, cancel_reason: str) -> models.Job:
        logger.info(f"User {user_id} attempting to cancel job {job_id}")
        job = self.db.query(models.Job).filter_by(id=job_id).first()

        if not job:
            logger.error(f"Job not found: job_id={job_id}")
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status in [JobStatus.COMPLETED, JobStatus.CANCELLED]:
            logger.warning(f"Invalid cancellation: job_id={job_id}, current_status={job.status}")
            raise HTTPException(status_code=400, detail="Cannot cancel this job")

        job.status = JobStatus.CANCELLED
        job.cancelled_at = datetime.now(timezone.utc)
        job.cancel_reason = cancel_reason
        self.db.commit()
        self.db.refresh(job)
        logger.info(f"Job cancelled: job_id={job.id}")
        return job

    # ---------------------------------------
    # List All Jobs for User
    # ---------------------------------------
    def get_all_jobs_for_user(self, user_id: UUID) -> List[models.Job]:
        logger.info(f"Fetching jobs for user_id={user_id}")
        return self.db.query(models.Job).filter(
            (models.Job.client_id == user_id) | (models.Job.worker_id == user_id)
        ).all()

    # ---------------------------------------
    # Get Job Detail
    # ---------------------------------------
    def get_job_detail(self, user_id: UUID, job_id: UUID) -> models.Job:
        logger.info(f"Fetching job detail: job_id={job_id}, user_id={user_id}")
        job = self.db.query(models.Job).filter_by(id=job_id).first()

        if not job:
            logger.error(f"Job not found: job_id={job_id}")
            raise HTTPException(status_code=404, detail="Job not found")

        if user_id not in [job.client_id, job.worker_id]:
            logger.warning(f"Unauthorized access to job_id={job_id} by user_id={user_id}")
            raise HTTPException(status_code=403, detail="Unauthorized access")

        return job
