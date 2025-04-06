"""
job/routes.py

Job-related API endpoints for both clients and workers:
- Accept a job
- Complete a job
- Cancel a job with reason
- List all jobs related to the current user
- Retrieve details of a specific job

All routes require authentication.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.job import schemas
from app.job.services import JobService
from app.database.session import get_db
from app.core.dependencies import get_current_user
from app.database.models import User
from main import limiter

router = APIRouter(prefix="/jobs", tags=["Jobs"])


# -----------------------------------
# Accept a Job
# -----------------------------------
@router.post("/{worker_id}/{service_id}/accept", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def accept_job(
    worker_id: UUID,
    service_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Allows a client to initiate a job by accepting a worker's service.
    """
    return JobService(db).accept_job(
        client_id=current_user.id,
        worker_id=worker_id,
        service_id=service_id
    )


# -----------------------------------
# Complete a Job
# -----------------------------------
@router.put("/{job_id}/complete", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
def complete_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Marks a job as completed by the client.
    """
    return JobService(db).complete_job(current_user.id, job_id)


# -----------------------------------
# Cancel a Job
# -----------------------------------
@router.put("/{job_id}/cancel", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
def cancel_job(
    job_id: UUID,
    payload: schemas.CancelJobRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancels a job with a provided reason.
    """
    return JobService(db).cancel_job(
        client_id=current_user.id,
        job_id=job_id,
        reason=payload.cancel_reason
    )


# -----------------------------------
# List All Jobs for Current User
# -----------------------------------
@router.get("", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
def get_jobs_for_user(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves all jobs (as client or worker) for the current user.
    """
    return JobService(db).get_all_jobs_for_user(current_user.id)


# -----------------------------------
# Get Job Details
# -----------------------------------
@router.get("/{job_id}", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
def get_job_detail(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves detailed information for a specific job involving the current user.
    """
    return JobService(db).get_job_detail(current_user.id, job_id)
