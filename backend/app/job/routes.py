"""
job/routes.py

Job-related API endpoints for both clients and workers:
- Create a job
- Accept a job
- Complete a job
- Cancel a job (with reason)
- List all jobs for current user
- Retrieve job details

All endpoints require authentication.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.database.session import get_db
from app.core.dependencies import get_current_user
from app.core.limiter import limiter
from app.job import schemas
from app.job.services import JobService

router = APIRouter(prefix="/jobs", tags=["Jobs"])

# Dependency alias
current_user = get_current_user


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
    current_user: User = Depends(current_user),
) -> schemas.JobRead:
    job = await JobService(db).create_job(client_id=current_user.id, payload=payload)
    return schemas.JobRead.model_validate(job)


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
    current_user: User = Depends(current_user),
) -> schemas.JobRead:
    payload.worker_id = current_user.id  # Ensure only the current user can accept as worker
    job = await JobService(db).accept_job(payload=payload)
    return schemas.JobRead.model_validate(job)


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
    current_user: User = Depends(current_user),
) -> schemas.JobRead:
    job = await JobService(db).complete_job(user_id=current_user.id, job_id=job_id)
    return schemas.JobRead.model_validate(job)


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
    current_user: User = Depends(current_user),
) -> schemas.JobRead:
    job = await JobService(db).cancel_job(
        user_id=current_user.id,
        job_id=job_id,
        cancel_reason=payload.cancel_reason,
    )
    return schemas.JobRead.model_validate(job)


@router.get(
    "",
    response_model=list[schemas.JobRead],
    status_code=status.HTTP_200_OK,
    summary="List My Jobs",
    description="Fetch all jobs where the authenticated user is the client or worker.",
)
@limiter.limit("5/minute")
async def get_jobs_for_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_user),
) -> list[schemas.JobRead]:
    jobs = await JobService(db).get_all_jobs_for_user(current_user.id)
    return [schemas.JobRead.model_validate(job) for job in jobs]


@router.get(
    "/{job_id}",
    response_model=schemas.JobRead,
    status_code=status.HTTP_200_OK,
    summary="Get Job Detail",
    description="Fetch full detail of a specific job associated with the authenticated user.",
)
@limiter.limit("5/minute")
async def get_job_detail(
    request: Request,
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_user),
) -> schemas.JobRead:
    job = await JobService(db).get_job_detail(user_id=current_user.id, job_id=job_id)
    return schemas.JobRead.model_validate(job)
