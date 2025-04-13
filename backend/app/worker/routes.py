"""
worker/routes.py

Worker module endpoints for:
- Profile management
- KYC document submission
- Job history and detail view
"""

from uuid import UUID

from fastapi import (
    APIRouter, Depends, UploadFile, File, Form, Request, status
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter
from app.worker.services import WorkerService
from app.worker import schemas
from app.core.dependencies import get_db, require_roles
from app.database.models import User, UserRole
from app.core.upload import upload_file_to_s3

router = APIRouter(prefix="/worker", tags=["Worker"])


# ----------------------------------------------------
# Profile Endpoints
# ----------------------------------------------------

@router.get(
    "/profile",
    response_model=schemas.WorkerProfileRead,
    status_code=status.HTTP_200_OK,
    summary="Get Worker Profile",
    description="Retrieve the authenticated worker's profile information."
)
@limiter.limit("10/minute")
async def get_worker_profile(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.WORKER, UserRole.ADMIN)),
):
    return await WorkerService(db).get_profile(current_user.id)


@router.patch(
    "/profile",
    response_model=schemas.WorkerProfileRead,
    status_code=status.HTTP_200_OK,
    summary="Update Worker Profile",
    description="Update profile information such as skills or experience for the authenticated worker."
)
@limiter.limit("5/minute")
async def update_worker_profile(
    request: Request,
    data: schemas.WorkerProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.WORKER, UserRole.ADMIN)),
):
    return await WorkerService(db).update_profile(current_user.id, data)


# ----------------------------------------------------
# KYC Endpoints
# ----------------------------------------------------

@router.get(
    "/kyc",
    status_code=status.HTTP_200_OK,
    summary="Get KYC Status",
    description="Fetch the submitted KYC status of the currently authenticated worker."
)
@limiter.limit("10/minute")
async def get_worker_kyc(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.WORKER, UserRole.ADMIN)),
):
    return await WorkerService(db).get_kyc(current_user.id)


@router.post(
    "/kyc",
    status_code=status.HTTP_201_CREATED,
    summary="Submit KYC Documents",
    description="Submit KYC documents including a document type, a document file, and a selfie."
)
@limiter.limit("3/minute")
async def submit_worker_kyc(
    request: Request,
    document_type: str = Form(...),
    document_file: UploadFile = File(...),
    selfie_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.WORKER, UserRole.ADMIN)),
):
    document_path = upload_file_to_s3(document_file, subfolder="kyc")
    selfie_path = upload_file_to_s3(selfie_file, subfolder="kyc")
    return await WorkerService(db).submit_kyc(
        user_id=current_user.id,
        document_type=document_type,
        document_path=document_path,
        selfie_path=selfie_path,
    )


# ----------------------------------------------------
# Job History Endpoints
# ----------------------------------------------------

@router.get(
    "/jobs",
    status_code=status.HTTP_200_OK,
    summary="List Worker Jobs",
    description="Returns a list of all jobs assigned to the currently authenticated worker."
)
@limiter.limit("10/minute")
async def list_worker_jobs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.WORKER, UserRole.ADMIN)),
):
    return await WorkerService(db).get_jobs(current_user.id)


@router.get(
    "/jobs/{job_id}",
    status_code=status.HTTP_200_OK,
    summary="Get Job Detail",
    description="Retrieve detailed information about a specific job assigned to the worker."
)
@limiter.limit("10/minute")
async def get_worker_job_detail(
    request: Request,
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.WORKER, UserRole.ADMIN)),
):
    return await WorkerService(db).get_job_detail(current_user.id, job_id)
