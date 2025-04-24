"""
worker/routes.py

Worker module endpoints for:
- Profile management
- KYC document submission
- Job history and detail view
"""

from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, File, Form, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.worker.services import WorkerService
from app.worker import schemas
from app.core.limiter import limiter
from app.core.dependencies import get_db
from app.database.models import User
from app.core.upload import upload_file_to_s3
from app.service.routes import require_worker_admin_roles
from app.job.schemas import JobRead
from app.worker.schemas import KYCRead

router = APIRouter(prefix="/worker", tags=["Worker"])

DBDep = Annotated[AsyncSession, Depends(get_db)]
WorkerDep = Annotated[User, Depends(require_worker_admin_roles)]

# ----------------------------------------------------
# Profile Endpoints
# ----------------------------------------------------


@router.get(
    "/profile",
    response_model=schemas.WorkerProfileRead,
    status_code=status.HTTP_200_OK,
    summary="Get Worker Profile",
    description="Retrieve the authenticated worker's profile information.",
)
@limiter.limit("10/minute")
async def get_worker_profile(
    request: Request,
    db: DBDep,
    current_user: WorkerDep,
) -> schemas.WorkerProfileRead:
    return await WorkerService(db).get_profile(current_user.id)


@router.patch(
    "/profile",
    response_model=schemas.WorkerProfileRead,
    status_code=status.HTTP_200_OK,
    summary="Update Worker Profile",
    description="Update profile information such as skills or experience for the authenticated worker.",
)
@limiter.limit("5/minute")
async def update_worker_profile(
    request: Request,
    data: schemas.WorkerProfileUpdate,
    db: DBDep,
    current_user: WorkerDep,
) -> schemas.WorkerProfileRead:
    return await WorkerService(db).update_profile(current_user.id, data)


# ----------------------------------------------------
# KYC Endpoints
# ----------------------------------------------------


@router.get(
    "/kyc",
    status_code=status.HTTP_200_OK,
    summary="Get KYC Status",
    description="Fetch the submitted KYC status of the currently authenticated worker.",
)
@limiter.limit("10/minute")
async def get_worker_kyc(
    request: Request,
    db: DBDep,
    current_user: WorkerDep,
) -> KYCRead | None:  # Corrected return type to KYCRead
    kyc = await WorkerService(db).get_kyc(current_user.id)
    if kyc:
        return KYCRead.model_validate(kyc)  # Convert model to schema
    return None


@router.post(
    "/kyc",
    status_code=status.HTTP_201_CREATED,
    summary="Submit KYC Documents",
    description="Submit KYC documents including a document type, a document file, and a selfie.",
)
@limiter.limit("3/minute")
async def submit_worker_kyc(
    request: Request,
    db: DBDep,
    current_user: WorkerDep,
    document_type: str = Form(...),
    document_file: UploadFile = File(...),
    selfie_file: UploadFile = File(...),
) -> KYCRead:  # Return type adjusted to KYCRead
    document_path = upload_file_to_s3(document_file, subfolder="kyc")
    selfie_path = upload_file_to_s3(selfie_file, subfolder="kyc")

    kyc = await WorkerService(db).submit_kyc(
        user_id=current_user.id,
        document_type=document_type,
        document_path=document_path,
        selfie_path=selfie_path,
    )
    return KYCRead.model_validate(kyc)  # Convert model to schema


# ----------------------------------------------------
# Job History Endpoints
# ----------------------------------------------------


@router.get(
    "/jobs",
    status_code=status.HTTP_200_OK,
    summary="List Worker Jobs",
    description="Returns a list of all jobs assigned to the currently authenticated worker.",
    response_model=list[JobRead],  # Use Pydantic schema for response
)
@limiter.limit("10/minute")
async def list_worker_jobs(
    request: Request,
    db: DBDep,
    current_user: WorkerDep,
) -> list[JobRead]:  # Corrected return type to JobRead
    jobs = await WorkerService(db).get_jobs(current_user.id)
    return [JobRead.model_validate(job) for job in jobs]


@router.get(
    "/jobs/{job_id}",
    status_code=status.HTTP_200_OK,
    summary="Get Job Detail",
    description="Retrieve detailed information about a specific job assigned to the worker.",
    response_model=JobRead,  # Use Pydantic schema for response
)
@limiter.limit("10/minute")
async def get_worker_job_detail(
    request: Request,
    job_id: UUID,
    db: DBDep,
    current_user: WorkerDep,
) -> JobRead:  # Corrected return type to JobRead
    job = await WorkerService(db).get_job_detail(job_id, current_user.id)
    return JobRead.model_validate(job)
