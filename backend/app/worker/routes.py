"""
worker/routes.py

Worker module endpoints for:
- Profile management
- KYC document submission
- Job history and detail view
"""

from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.admin.schemas import PresignedUrlResponse
from app.database.enums import UserRole
from app.worker.services import WorkerService
from app.worker import schemas
from app.core.limiter import limiter
from app.core.dependencies import get_db, get_current_user
from app.database.models import User
from app.core.upload import upload_file_to_s3
from app.job.schemas import JobRead
from app.worker.schemas import KYCRead

router = APIRouter(prefix="/worker", tags=["Worker"])
logger = logging.getLogger(__name__)

DBDep = Annotated[AsyncSession, Depends(get_db)]
WorkerDep = Annotated[User, Depends(get_current_user)]


# ----------------------------------------------------
# Profile Endpoints
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
    current_user: WorkerDep,
) -> schemas.WorkerProfileRead:
    if current_user.role != UserRole.WORKER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    return await WorkerService(db).get_profile(current_user.id)


@router.patch(
    "/profile",
    response_model=schemas.WorkerProfileRead,
    status_code=status.HTTP_200_OK,
    summary="Update My Worker Profile",
    description="Update profile information (excluding picture) for the authenticated worker.",
)
@limiter.limit("5/minute")
async def update_my_worker_profile(
    request: Request,
    data: schemas.WorkerProfileUpdate,
    db: DBDep,
    current_user: WorkerDep,
) -> schemas.WorkerProfileRead:
    if current_user.role != UserRole.WORKER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
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
    current_user: WorkerDep,
    profile_picture: UploadFile = File(
        ..., description="New profile picture file (JPG, PNG). Max 10MB."
    ),
) -> schemas.MessageResponse:
    """
    Handles uploading and setting a new profile picture for the worker.
    """
    logger = logging.getLogger(__name__)
    if current_user.role != UserRole.WORKER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    logger.info(f"Worker {current_user.id} attempting to update profile picture.")

    picture_url = await upload_file_to_s3(profile_picture, subfolder="profile_pictures")

    await WorkerService(db).update_profile_picture(current_user.id, picture_url)

    logger.info(f"Worker {current_user.id} successfully updated profile picture to {picture_url}")
    return schemas.MessageResponse(detail="Profile picture updated successfully.")


# ----------------------------------------------------
# KYC Endpoints
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
    current_user: WorkerDep,
) -> KYCRead | None:
    if current_user.role != UserRole.WORKER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    kyc_model = await WorkerService(db).get_kyc(current_user.id)
    if kyc_model:
        return KYCRead.model_validate(kyc_model, from_attributes=True)
    return None


@router.post(
    "/kyc",
    response_model=KYCRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit My KYC Documents",
    description="Submit or update KYC documents including a document type, a document file, and a selfie.",
)
@limiter.limit("3/hour")
async def submit_my_kyc(
    request: Request,
    db: DBDep,
    current_user: WorkerDep,
    document_type: str = Form(
        ...,
        description="Type of identification document being uploaded (e.g., 'Passport', 'Driver\\'s License', 'National ID Card').",
    ),
    document_file: UploadFile = File(
        ..., description="The identification document file (PDF, JPG, PNG). Max 10MB."
    ),
    selfie_file: UploadFile = File(..., description="A clear selfie image (JPG, PNG). Max 10MB."),
) -> KYCRead:
    if current_user.role != UserRole.WORKER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    document_path = await upload_file_to_s3(document_file, subfolder="kyc")
    selfie_path = await upload_file_to_s3(selfie_file, subfolder="kyc")

    kyc_model = await WorkerService(db).submit_kyc(
        user_id=current_user.id,
        document_type=document_type,
        document_path=document_path,
        selfie_path=selfie_path,
    )
    return KYCRead.model_validate(kyc_model, from_attributes=True)


@router.get(
    "/profile/picture-url",
    response_model=PresignedUrlResponse | None,
    status_code=status.HTTP_200_OK,
    summary="Get Pre-signed URL for My Profile Picture",
    description="Retrieves a temporary, secure URL to view the authenticated worker's profile picture.",
)
@limiter.limit("30/minute")
async def get_my_worker_profile_picture_url(
    request: Request,
    db: DBDep,
    current_user: WorkerDep,
) -> PresignedUrlResponse | None:
    """
    Generates and returns a pre-signed URL for the worker's profile picture.
    Returns null if the user has no profile picture set.
    """
    logger.info(f"Worker {current_user.id} requesting pre-signed URL for their profile picture.")
    presigned_url = await WorkerService(db).get_profile_picture_presigned_url(current_user.id)

    if not presigned_url:
        return None

    return PresignedUrlResponse(url=presigned_url)  # type: ignore[arg-type]


# ----------------------------------------------------
# Job History Endpoints (Keep as is, use WorkerDep)
# ----------------------------------------------------
@router.get(
    "/jobs",
    response_model=list[JobRead],
    status_code=status.HTTP_200_OK,
    summary="List My Worker Jobs",
    description="Returns a list of all jobs assigned to the currently authenticated worker.",
)
@limiter.limit("10/minute")
async def list_my_worker_jobs(
    request: Request,
    db: DBDep,
    current_user: WorkerDep,
) -> list[JobRead]:
    if current_user.role != UserRole.WORKER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    job_models = await WorkerService(db).get_jobs(current_user.id)
    return [JobRead.model_validate(job, from_attributes=True) for job in job_models]


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
    current_user: WorkerDep,
) -> JobRead:
    if current_user.role != UserRole.WORKER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    job_model = await WorkerService(db).get_job_detail(current_user.id, job_id)
    return JobRead.model_validate(job_model, from_attributes=True)
