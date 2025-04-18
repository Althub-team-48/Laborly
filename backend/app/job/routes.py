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
from typing import List

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.job import schemas
from app.job.services import JobService
from app.database.session import get_db
from app.core.dependencies import get_current_user
from app.database.models import User
from app.core.limiter import limiter

router = APIRouter(prefix="/jobs", tags=["Jobs"])

current_user= get_current_user
# ---------------------------
# Create Job (Client)
# ---------------------------
@router.post(
    "/create",
    response_model=schemas.JobRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Job",
    description="Client creates a job when initiating a conversation with a worker.",
)
@limiter.limit("5/minute")
async def create_job(
    request: Request,
    payload: schemas.JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_user)
):
    client_id = current_user.id
    return await JobService(db).create_job(client_id=client_id, payload=payload)

# ---------------------------
# Accept Job (Worker)
# ---------------------------
@router.post(
    "/accept",
    response_model=schemas.JobRead,
    status_code=status.HTTP_200_OK,
    summary="Accept Job",
    description="Worker accepts a job previously created by a client.",
)
@limiter.limit("5/minute")
async def accept_job(
    request: Request,
    payload: schemas.JobAccept,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_user)
):
    payload.worker_id = current_user.id
    return await JobService(db).accept_job(payload=payload)


# ---------------------------
# Complete Job
# ---------------------------
@router.put(
    "/{job_id}/complete",
    response_model=schemas.JobRead,
    status_code=status.HTTP_200_OK,
    summary="Complete Job",
    description="Worker marks a job as completed.",
)
@limiter.limit("5/minute")
async def complete_job(
    request: Request,
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_user)
):
    return await JobService(db).complete_job(current_user.id, job_id)


# ---------------------------
# Cancel Job
# ---------------------------
@router.put(
    "/{job_id}/cancel",
    response_model=schemas.JobRead,
    status_code=status.HTTP_200_OK,
    summary="Cancel Job",
    description="Client cancels a job and provides a reason for cancellation.",
)
@limiter.limit("5/minute")
async def cancel_job(
    request: Request,
    job_id: UUID,
    payload: schemas.CancelJobRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_user)
):
    return await JobService(db).cancel_job(
        user_id=current_user.id,
        job_id=job_id,
        cancel_reason=payload.cancel_reason
    )


# ---------------------------
# List Jobs for Current User
# ---------------------------
@router.get(
    "",
    response_model=List[schemas.JobRead],
    status_code=status.HTTP_200_OK,
    summary="List My Jobs",
    description="Retrieve all jobs associated with the currently authenticated user (client or worker).",
)
@limiter.limit("5/minute")
async def get_jobs_for_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_user)
):
    return await JobService(db).get_all_jobs_for_user(current_user.id)


# ---------------------------
# Get Job Details
# ---------------------------
@router.get(
    "/{job_id}",
    response_model=schemas.JobRead,
    status_code=status.HTTP_200_OK,
    summary="Get Job Detail",
    description="Retrieve full details for a specific job related to the authenticated user.",
)
@limiter.limit("5/minute")
async def get_job_detail(
    request: Request,
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_user)
):
    return await JobService(db).get_job_detail(current_user.id, job_id)
