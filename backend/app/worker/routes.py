"""
backend/app/worker/routes.py

Worker Routes
Defines all public and authenticated endpoints for worker profile management,
KYC processing, profile picture handling, and job history retrieval.
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.schemas import PresignedUrlResponse
from app.core.dependencies import get_current_user_with_role, PaginationParams
from app.core.schemas import PaginatedResponse
from app.core.limiter import limiter
from app.core.upload import upload_file_to_s3
from app.database.enums import UserRole
from app.database.models import User
from app.database.session import get_db
from app.job.schemas import JobRead
from app.worker import schemas
from app.worker.schemas import KYCRead, PublicWorkerRead
from app.worker.services import WorkerService

router = APIRouter(prefix="/worker", tags=["Worker"])
logger = logging.getLogger(__name__)

DBDep = Annotated[AsyncSession, Depends(get_db)]
AuthenticatedWorkerDep = Annotated[User, Depends(get_current_user_with_role(UserRole.WORKER))]


# ----------------------------------------------------
# Public Profile Endpoints
# ----------------------------------------------------
@router.get(
    "/{user_id}/public",
    response_model=PublicWorkerRead,
    status_code=status.HTTP_200_OK,
    summary="Get Public Worker Profile",
    description="Retrieve publicly available profile information for a specific worker.",
)
@limiter.limit("30/minute")
async def get_public_worker_profile(
    request: Request,
    user_id: UUID,
    db: DBDep,
) -> PublicWorkerRead:
    """
    Retrieve the public worker profile for the specified user ID.
    No authentication required.
    """
    return await WorkerService(db).get_public_worker_profile(user_id)


# ----------------------------------------------------
# Authenticated Profile Endpoints
# ----------------------------------------------------
@router.get(
    "/profile",
    response_model=schemas.WorkerProfileRead,
    status_code=status.HTTP_200_OK,
    summary="Get My Worker Profile",
    description="Retrieve the authenticated worker's profile information.",
)
@limiter.limit("10/minute")
async def get_my_worker_profile(
    request: Request,
    db: DBDep,
    current_user: AuthenticatedWorkerDep,
) -> schemas.WorkerProfileRead:
    """
    Retrieve the authenticated worker's profile.
    """
    return await WorkerService(db).get_profile(current_user.id)


@router.patch(
    "/profile",
    response_model=schemas.WorkerProfileRead,
    status_code=status.HTTP_200_OK,
    summary="Update My Worker Profile",
    description="Update profile information (excluding profile picture) for the authenticated worker.",
)
@limiter.limit("5/minute")
async def update_my_worker_profile(
    request: Request,
    data: schemas.WorkerProfileUpdate,
    db: DBDep,
    current_user: AuthenticatedWorkerDep,
) -> schemas.WorkerProfileRead:
    """
    Update the authenticated worker's profile.
    """
    return await WorkerService(db).update_profile(current_user.id, data)


@router.patch(
    "/profile/picture",
    response_model=schemas.MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Update My Profile Picture",
    description="Upload and update the profile picture for the authenticated worker.",
)
@limiter.limit("5/hour")
async def update_my_worker_profile_picture(
    request: Request,
    db: DBDep,
    current_user: AuthenticatedWorkerDep,
    profile_picture: UploadFile = File(
        ..., description="New profile picture file (JPG, PNG). Max 10MB."
    ),
) -> schemas.MessageResponse:
    """
    Upload a new profile picture for the authenticated worker.
    """
    logger.info(f"Worker {current_user.id} attempting to update profile picture.")

    picture_url = await upload_file_to_s3(profile_picture, subfolder="profile_pictures")

    await WorkerService(db).update_profile_picture(current_user.id, picture_url)

    logger.info(f"Worker {current_user.id} successfully updated profile picture to {picture_url}.")
    return schemas.MessageResponse(detail="Profile picture updated successfully.")


@router.get(
    "/profile/picture-url",
    response_model=PresignedUrlResponse | None,
    status_code=status.HTTP_200_OK,
    summary="Get Pre-signed URL for My Profile Picture",
    description="Retrieve a temporary, secure URL to view the authenticated worker's profile picture.",
)
@limiter.limit("30/minute")
async def get_my_worker_profile_picture_url(
    request: Request,
    db: DBDep,
    current_user: AuthenticatedWorkerDep,
) -> PresignedUrlResponse | None:
    """
    Generate a pre-signed URL for the worker's profile picture.
    Returns None if no profile picture is set.
    """
    logger.info(f"Worker {current_user.id} requesting pre-signed URL for their profile picture.")

    presigned_url = await WorkerService(db).get_profile_picture_presigned_url(current_user.id)

    if not presigned_url:
        return None

    return PresignedUrlResponse(url=presigned_url)  # type: ignore[arg-type]


# ----------------------------------------------------
# KYC Endpoints (Authenticated Worker)
# ----------------------------------------------------
@router.get(
    "/kyc",
    response_model=KYCRead | None,
    status_code=status.HTTP_200_OK,
    summary="Get My KYC Status",
    description="Fetch the status and details of the authenticated worker's KYC submission.",
)
@limiter.limit("10/minute")
async def get_my_kyc(
    request: Request,
    db: DBDep,
    current_user: AuthenticatedWorkerDep,
) -> KYCRead | None:
    """
    Retrieve KYC information for the authenticated worker.
    """
    kyc_model = await WorkerService(db).get_kyc(current_user.id)
    if kyc_model:
        return KYCRead.model_validate(kyc_model, from_attributes=True)
    return None


@router.post(
    "/kyc",
    response_model=KYCRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit My KYC Documents",
    description="Submit or update KYC documents including document type, document file, and selfie.",
)
@limiter.limit("3/hour")
async def submit_my_kyc(
    request: Request,
    db: DBDep,
    current_user: AuthenticatedWorkerDep,
    document_type: str = Form(
        ...,
        description="Type of identification document (e.g., Passport, Driver's License, National ID Card).",
    ),
    document_file: UploadFile = File(
        ..., description="The identification document file (PDF, JPG, PNG). Max 10MB."
    ),
    selfie_file: UploadFile = File(..., description="A clear selfie image (JPG, PNG). Max 10MB."),
) -> KYCRead:
    """
    Submit KYC documents for the authenticated worker.
    """
    document_path = await upload_file_to_s3(document_file, subfolder="kyc")
    selfie_path = await upload_file_to_s3(selfie_file, subfolder="kyc")

    kyc_model = await WorkerService(db).submit_kyc(
        user_id=current_user.id,
        document_type=document_type,
        document_path=document_path,
        selfie_path=selfie_path,
    )
    return KYCRead.model_validate(kyc_model, from_attributes=True)


# ----------------------------------------------------
# Job History Endpoints (Authenticated Worker)
# ----------------------------------------------------
@router.get(
    "/jobs",
    response_model=PaginatedResponse[JobRead],
    status_code=status.HTTP_200_OK,
    summary="List My Worker Jobs",
    description="Return a list of all jobs assigned to the currently authenticated worker.",
)
@limiter.limit("10/minute")
async def list_my_worker_jobs(
    request: Request,
    db: DBDep,
    current_user: AuthenticatedWorkerDep,
    pagination: PaginationParams = Depends(),
) -> PaginatedResponse[JobRead]:
    """
    List all jobs assigned to the authenticated worker with pagination.
    """
    job_models, total_count = await WorkerService(db).get_jobs(
        current_user.id, skip=pagination.skip, limit=pagination.limit
    )
    return PaginatedResponse(
        total_count=total_count,
        has_next_page=(pagination.skip + pagination.limit) < total_count,
        items=[JobRead.model_validate(job, from_attributes=True) for job in job_models],
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobRead,
    status_code=status.HTTP_200_OK,
    summary="Get My Job Detail",
    description="Retrieve detailed information about a specific job assigned to the authenticated worker.",
)
@limiter.limit("10/minute")
async def get_my_worker_job_detail(
    request: Request,
    job_id: UUID,
    db: DBDep,
    current_user: AuthenticatedWorkerDep,
) -> JobRead:
    """
    Retrieve details about a specific job assigned to the authenticated worker.
    """
    job_model = await WorkerService(db).get_job_detail(current_user.id, job_id)
    return JobRead.model_validate(job_model, from_attributes=True)
