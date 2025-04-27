"""
backend/app/job/routes.py

Job Routes
Defines job-related API endpoints for clients and workers:
- Create a job (Authenticated Client)
- Accept a job (Authenticated Worker)
- Complete a job (Authenticated Worker)
- Cancel a job (Authenticated Client)
- List all jobs for current user (Authenticated Client/Worker)
- Retrieve job details (Authenticated Client/Worker)

All endpoints require authentication.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import PaginationParams, get_current_user_with_role, require_roles
from app.core.limiter import limiter
from app.core.schemas import PaginatedResponse
from app.database.enums import UserRole
from app.database.models import User
from app.database.session import get_db
from app.job import schemas
from app.job.services import JobService

router = APIRouter(prefix="/jobs", tags=["Jobs"])

DBDep = Annotated[AsyncSession, Depends(get_db)]

AuthenticatedClientDep = Annotated[User, Depends(get_current_user_with_role(UserRole.CLIENT))]
AuthenticatedWorkerDep = Annotated[User, Depends(get_current_user_with_role(UserRole.WORKER))]
AuthenticatedClientOrWorkerDep = Annotated[
    User, Depends(require_roles(UserRole.CLIENT, UserRole.WORKER))
]


# ---------------------------------------------------
# Client Endpoints (Create, Cancel Job)
# ---------------------------------------------------


@router.post(
    "/create",
    response_model=schemas.JobRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Job",
    description="Client creates a job when initiating work with a worker. Requires Client role.",
)
@limiter.limit("5/minute")
async def create_job(
    request: Request,
    payload: schemas.JobCreate,
    db: DBDep,
    current_user: AuthenticatedClientDep,
) -> schemas.JobRead:
    """Authenticated client creates a new job."""
    job = await JobService(db).create_job(client_id=current_user.id, payload=payload)
    return schemas.JobRead.model_validate(job)


@router.put(
    "/{job_id}/cancel",
    response_model=schemas.JobRead,
    status_code=status.HTTP_200_OK,
    summary="Cancel Job",
    description="Client cancels a job and provides a reason. Requires Client role.",
)
@limiter.limit("5/minute")
async def cancel_job(
    request: Request,
    job_id: UUID,
    payload: schemas.CancelJobRequest,
    db: DBDep,
    current_user: AuthenticatedClientDep,
) -> schemas.JobRead:
    """Authenticated client cancels an existing job."""
    job = await JobService(db).cancel_job(
        user_id=current_user.id,
        job_id=job_id,
        cancel_reason=payload.cancel_reason,
    )
    return schemas.JobRead.model_validate(job)


# ---------------------------------------------------
# Worker Endpoints (Accept, Complete Job)
# ---------------------------------------------------


@router.post(
    "/accept",
    response_model=schemas.JobRead,
    status_code=status.HTTP_200_OK,
    summary="Accept Job",
    description="Worker accepts a job posted by a client. Requires Worker role.",
)
@limiter.limit("5/minute")
async def accept_job(
    request: Request,
    payload: schemas.JobAccept,
    db: DBDep,
    current_user: AuthenticatedWorkerDep,
) -> schemas.JobRead:
    """Authenticated worker accepts an assigned job."""
    job = await JobService(db).accept_job(worker_id=current_user.id, job_id=payload.job_id)
    return schemas.JobRead.model_validate(job)


@router.put(
    "/{job_id}/complete",
    response_model=schemas.JobRead,
    status_code=status.HTTP_200_OK,
    summary="Complete Job",
    description="Worker marks a job as completed. Requires Worker role.",
)
@limiter.limit("5/minute")
async def complete_job(
    request: Request,
    job_id: UUID,
    db: DBDep,
    current_user: AuthenticatedWorkerDep,
) -> schemas.JobRead:
    """Authenticated worker marks a job as completed."""
    job = await JobService(db).complete_job(worker_id=current_user.id, job_id=job_id)
    return schemas.JobRead.model_validate(job)


# ---------------------------------------------------
# Shared Endpoints (Client or Worker)
# ---------------------------------------------------
@router.get(
    "",
    response_model=PaginatedResponse[schemas.JobRead],
    status_code=status.HTTP_200_OK,
    summary="List My Jobs",
    description="List all jobs for the authenticated user (client or worker).",
)
@limiter.limit("5/minute")
async def get_jobs_for_user(
    request: Request,
    db: DBDep,
    current_user: AuthenticatedClientOrWorkerDep,
    pagination: PaginationParams = Depends(),
) -> PaginatedResponse[schemas.JobRead]:
    """List all jobs where the authenticated user is involved (client or worker) with pagination."""
    jobs, total_count = await JobService(db).get_all_jobs_for_user(
        current_user.id, skip=pagination.skip, limit=pagination.limit
    )
    return PaginatedResponse(
        total_count=total_count,
        has_next_page=(pagination.skip + pagination.limit) < total_count,
        items=[schemas.JobRead.model_validate(job) for job in jobs],
    )


@router.get(
    "/{job_id}",
    response_model=schemas.JobRead,
    status_code=status.HTTP_200_OK,
    summary="Get Job Detail",
    description="Fetch full detail of a job associated with the authenticated user (client or worker).",
)
@limiter.limit("5/minute")
async def get_job_detail(
    request: Request,
    job_id: UUID,
    db: DBDep,
    current_user: AuthenticatedClientOrWorkerDep,
) -> schemas.JobRead:
    """Fetch full detail of a specific job for the authenticated user."""
    job = await JobService(db).get_job_detail(user_id=current_user.id, job_id=job_id)
    return schemas.JobRead.model_validate(job)
