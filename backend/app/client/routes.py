"""
client/routes.py

Defines routes under the Client module for:
- Profile management
- Favorite worker handling
- Client job history and job details
"""

import logging
from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.schemas import PresignedUrlResponse
from app.client import schemas
from app.client.schemas import MessageResponse
from app.client.services import ClientService
from app.core.dependencies import get_db, get_current_user
from app.core.limiter import limiter
from app.database.enums import UserRole
from app.database.models import User
from app.core.upload import upload_file_to_s3

# ---------------------------------------------------
# Router Configuration
# ---------------------------------------------------
router = APIRouter(prefix="/client", tags=["Client"])
logger = logging.getLogger(__name__)

# ---------------------------------------------------
# Dependencies
# ---------------------------------------------------
ClientDep = Annotated[User, Depends(get_current_user)]
DBDep = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------
# Client Profile Endpoints
# ---------------------------------------------------
@router.get(
    "/profile",
    response_model=schemas.ClientProfileRead,
    status_code=status.HTTP_200_OK,
    summary="Get My Client Profile",
    description="Retrieve the profile of the currently authenticated client user.",
)
@limiter.limit("10/minute")
async def get_my_client_profile(
    request: Request,
    db: DBDep,
    current_user: ClientDep,
) -> schemas.ClientProfileRead:
    """
    Retrieves the client profile for the authenticated user.
    """
    return await ClientService(db).get_profile(current_user.id)


@router.patch(
    "/profile",
    response_model=schemas.ClientProfileRead,
    status_code=status.HTTP_200_OK,
    summary="Update My Client Profile",
    description="Update fields in the authenticated client's profile (excluding picture).",
)
@limiter.limit("5/minute")
async def update_my_client_profile(
    request: Request,
    data: schemas.ClientProfileUpdate,
    db: DBDep,
    current_user: ClientDep,
) -> schemas.ClientProfileRead:
    """
    Updates the client profile fields (non-picture) for the authenticated user.
    """
    return await ClientService(db).update_profile(current_user.id, data)


@router.patch(
    "/profile/picture",
    response_model=schemas.MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Update My Profile Picture",
    description="Upload and update the profile picture for the authenticated client.",
)
@limiter.limit("5/hour")
async def update_my_client_profile_picture(
    request: Request,
    db: DBDep,
    current_user: ClientDep,
    profile_picture: UploadFile = File(
        ..., description="New profile picture file (JPG, PNG). Max 10MB."
    ),
) -> schemas.MessageResponse:
    """
    Handles uploading and setting a new profile picture.
    """
    logger.info(f"Client {current_user.id} attempting to update profile picture.")

    picture_url = await upload_file_to_s3(profile_picture, subfolder="profile_pictures")

    await ClientService(db).update_profile_picture(current_user.id, picture_url)

    logger.info(f"Client {current_user.id} successfully updated profile picture to {picture_url}")
    return schemas.MessageResponse(detail="Profile picture updated successfully.")


@router.get(
    "/profile/picture-url",
    response_model=PresignedUrlResponse | None,
    status_code=status.HTTP_200_OK,
    summary="Get Pre-signed URL for My Profile Picture",
    description="Retrieves a temporary, secure URL to view the authenticated client's profile picture.",
)
@limiter.limit("30/minute")
async def get_my_client_profile_picture_url(
    request: Request,
    db: DBDep,
    current_user: ClientDep,
) -> PresignedUrlResponse | None:
    """
    Generates and returns a pre-signed URL for the client's profile picture.
    Returns null if the user has no profile picture set.
    """
    if current_user.role != UserRole.CLIENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    logger.info(f"Client {current_user.id} requesting pre-signed URL for their profile picture.")
    presigned_url = await ClientService(db).get_profile_picture_presigned_url(current_user.id)

    if not presigned_url:
        return None

    return PresignedUrlResponse(url=presigned_url)  # type: ignore[arg-type]


# ---------------------------------------------------
# Favorite Workers Endpoints (Keep as is, use ClientDep)
# ---------------------------------------------------
@router.get(
    "/favorites",
    response_model=list[schemas.FavoriteRead],
    status_code=status.HTTP_200_OK,
    summary="List My Favorite Workers",
    description="Retrieve a list of workers the authenticated client has marked as favorites.",
)
@limiter.limit("10/minute")
async def list_my_favorite_workers(
    request: Request,
    db: DBDep,
    current_user: ClientDep,
) -> list[schemas.FavoriteRead]:
    favorites = await ClientService(db).list_favorites(current_user.id)
    return [schemas.FavoriteRead.model_validate(fav, from_attributes=True) for fav in favorites]


@router.post(
    "/favorites/{worker_id}",
    response_model=schemas.FavoriteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add Favorite Worker",
    description="Add a specific worker to the authenticated client's list of favorites.",
)
@limiter.limit("5/minute")
async def add_my_favorite_worker(
    request: Request,
    worker_id: UUID,
    db: DBDep,
    current_user: ClientDep,
) -> schemas.FavoriteRead:
    fav = await ClientService(db).add_favorite(current_user.id, worker_id)
    return schemas.FavoriteRead.model_validate(fav, from_attributes=True)


@router.delete(
    "/favorites/{worker_id}",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponse,
    summary="Remove Favorite Worker",
    description="Remove a worker from the authenticated client's list of favorites.",
)
@limiter.limit("5/minute")
async def remove_my_favorite_worker(
    request: Request,
    worker_id: UUID,
    db: DBDep,
    current_user: ClientDep,
) -> MessageResponse:
    await ClientService(db).remove_favorite(current_user.id, worker_id)
    return MessageResponse(detail="Favorite worker removed successfully.")


# ---------------------------------------------------
# Job History Endpoints
# ---------------------------------------------------
@router.get(
    "/jobs",
    response_model=list[schemas.ClientJobRead],
    status_code=status.HTTP_200_OK,
    summary="List My Client Jobs",
    description="List all jobs created by the authenticated client user.",
)
@limiter.limit("10/minute")
async def list_my_client_jobs(
    request: Request,
    db: DBDep,
    current_user: ClientDep,
) -> list[schemas.ClientJobRead]:
    jobs = await ClientService(db).get_jobs(current_user.id)
    return [schemas.ClientJobRead.model_validate(job, from_attributes=True) for job in jobs]


@router.get(
    "/jobs/{job_id}",
    response_model=schemas.ClientJobRead,
    status_code=status.HTTP_200_OK,
    summary="Get My Job Detail",
    description="Get detailed information for a specific job posted by the authenticated client.",
)
@limiter.limit("10/minute")
async def get_my_client_job_detail(
    request: Request,
    job_id: UUID,
    db: DBDep,
    current_user: ClientDep,
) -> schemas.ClientJobRead:
    job = await ClientService(db).get_job_detail(current_user.id, job_id)
    return schemas.ClientJobRead.model_validate(job, from_attributes=True)
