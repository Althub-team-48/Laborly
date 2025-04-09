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

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.job import schemas
from app.job.services import JobService
from app.database.session import get_db
from app.core.dependencies import get_current_user
from app.database.models import User
from app.core.limiter import limiter

router = APIRouter(prefix="/jobs", tags=["Jobs"])


# ---------------------------
# Accept Job
# ---------------------------
@router.post("/{worker_id}/{service_id}/accept", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def accept_job(
    request: Request,
    worker_id: UUID,
    service_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Client initiates a job request for a specific worker and service.
    """
    return await JobService(db).accept_job(
        client_id=current_user.id,
        worker_id=worker_id,
        service_id=service_id
    )


# ---------------------------
# Complete Job
# ---------------------------
@router.put("/{job_id}/complete", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def complete_job(
    request: Request,
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Worker marks a job as completed.
    """
    return await JobService(db).complete_job(current_user.id, job_id)


# ---------------------------
# Cancel Job
# ---------------------------
@router.put("/{job_id}/cancel", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def cancel_job(
    request: Request,
    job_id: UUID,
    payload: schemas.CancelJobRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Client cancels a job with a reason.
    """
    return await JobService(db).cancel_job(
        client_id=current_user.id,
        job_id=job_id,
        reason=payload.cancel_reason
    )


# ---------------------------
# List Jobs for Current User
# ---------------------------
@router.get("", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def get_jobs_for_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns all jobs related to the authenticated user (client or worker).
    """
    return await JobService(db).get_all_jobs_for_user(current_user.id)


# ---------------------------
# Get Job Details
# ---------------------------
@router.get("/{job_id}", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def get_job_detail(
    request: Request,
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve detailed information about a specific job.
    """
    return await JobService(db).get_job_detail(current_user.id, job_id)
