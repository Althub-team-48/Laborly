"""
backend/app/client/routes.py

Client Routes
Defines API routes under the Client module for:
- Profile management (authenticated and public)
- Favorite worker handling
- Client job history and job details
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from myapp.admin.schemas import PresignedUrlResponse
from myapp.client import schemas
from myapp.client.schemas import MessageResponse, PublicClientRead
from myapp.client.services import ClientService
from myapp.core.dependencies import get_current_user_with_role, PaginationParams
from myapp.core.limiter import limiter
from myapp.core.upload import upload_file_to_s3
from myapp.core.schemas import PaginatedResponse
from myapp.database.enums import UserRole
from myapp.database.models import User
from myapp.database.session import get_db

router = APIRouter(prefix="/client", tags=["Client"])
logger = logging.getLogger(__name__)

DBDep = Annotated[AsyncSession, Depends(get_db)]
AuthenticatedClientDep = Annotated[User, Depends(get_current_user_with_role(UserRole.CLIENT))]


# ---------------------------------------------------
# Public Client Profile Endpoint
# ---------------------------------------------------
@router.get(
    "/{user_id}/public",
    response_model=PublicClientRead,
    status_code=status.HTTP_200_OK,
    summary="Get Public Client Profile",
    description="Retrieve publicly available profile information for a specific client.",
)
@limiter.limit("30/minute")
async def get_public_client_profile(
    request: Request,
    user_id: UUID,
    db: DBDep,
) -> PublicClientRead:
    """Retrieve public client profile by user ID (no authentication required)."""
    return await ClientService(db).get_public_client_profile(user_id)


# ---------------------------------------------------
# Authenticated Client Profile Endpoints
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
    current_user: AuthenticatedClientDep,
) -> schemas.ClientProfileRead:
    """Retrieve the authenticated client's profile."""
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
    current_user: AuthenticatedClientDep,
) -> schemas.ClientProfileRead:
    """Update the authenticated client's profile information."""
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
    current_user: AuthenticatedClientDep,
    profile_picture: UploadFile = File(
        ..., description="New profile picture file (JPG, PNG). Max 10MB."
    ),
) -> schemas.MessageResponse:
    """Upload and set a new profile picture for the authenticated client."""
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
    description="Retrieve a temporary, secure URL to view the authenticated client's profile picture.",
)
@limiter.limit("30/minute")
async def get_my_client_profile_picture_url(
    request: Request,
    db: DBDep,
    current_user: AuthenticatedClientDep,
) -> PresignedUrlResponse | None:
    """Generate a pre-signed URL for the client's profile picture."""
    logger.info(f"Client {current_user.id} requesting pre-signed URL for their profile picture.")

    presigned_url = await ClientService(db).get_profile_picture_presigned_url(current_user.id)

    if not presigned_url:
        return None

    return PresignedUrlResponse(url=presigned_url)  # type: ignore[arg-type]


# ---------------------------------------------------
# Favorite Workers Endpoints (Authenticated Client)
# ---------------------------------------------------
@router.get(
    "/favorites",
    response_model=PaginatedResponse[schemas.FavoriteRead],
    status_code=status.HTTP_200_OK,
    summary="List My Favorite Workers",
    description="Retrieve a list of workers the authenticated client has marked as favorites.",
)
@limiter.limit("10/minute")
async def list_my_favorite_workers(
    request: Request,
    db: DBDep,
    current_user: AuthenticatedClientDep,
    pagination: PaginationParams = Depends(),
) -> PaginatedResponse[schemas.FavoriteRead]:
    """List all favorite workers for the authenticated client with pagination."""
    favorites, total_count = await ClientService(db).list_favorites(
        current_user.id, skip=pagination.skip, limit=pagination.limit
    )
    return PaginatedResponse(
        total_count=total_count,
        has_next_page=(pagination.skip + pagination.limit) < total_count,
        items=[schemas.FavoriteRead.model_validate(fav, from_attributes=True) for fav in favorites],
    )


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
    current_user: AuthenticatedClientDep,
) -> schemas.FavoriteRead:
    """Add a worker to the authenticated client's favorites."""
    fav = await ClientService(db).add_favorite(current_user.id, worker_id)
    return schemas.FavoriteRead.model_validate(fav, from_attributes=True)


@router.delete(
    "/favorites/{worker_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove Favorite Worker",
    description="Remove a worker from the authenticated client's list of favorites.",
)
@limiter.limit("5/minute")
async def remove_my_favorite_worker(
    request: Request,
    worker_id: UUID,
    db: DBDep,
    current_user: AuthenticatedClientDep,
) -> MessageResponse:
    """Remove a worker from the authenticated client's favorites."""
    await ClientService(db).remove_favorite(current_user.id, worker_id)
    return MessageResponse(detail="Favorite worker removed successfully.")


# ---------------------------------------------------
# Job History Endpoints (Authenticated Client)
# ---------------------------------------------------
@router.get(
    "/jobs",
    response_model=PaginatedResponse[schemas.ClientJobRead],
    status_code=status.HTTP_200_OK,
    summary="List My Client Jobs",
    description="List all jobs created by the authenticated client user.",
)
@limiter.limit("10/minute")
async def list_my_client_jobs(
    request: Request,
    db: DBDep,
    current_user: AuthenticatedClientDep,
    pagination: PaginationParams = Depends(),
) -> PaginatedResponse[schemas.ClientJobRead]:
    """List all jobs posted by the authenticated client with pagination."""
    jobs, total_count = await ClientService(db).get_jobs(
        current_user.id, skip=pagination.skip, limit=pagination.limit
    )
    return PaginatedResponse(
        total_count=total_count,
        has_next_page=(pagination.skip + pagination.limit) < total_count,
        items=[schemas.ClientJobRead.model_validate(job, from_attributes=True) for job in jobs],
    )


@router.get(
    "/jobs/{job_id}",
    response_model=schemas.ClientJobRead,
    status_code=status.HTTP_200_OK,
    summary="Get My Job Detail",
    description="Retrieve detailed information for a specific job posted by the authenticated client.",
)
@limiter.limit("10/minute")
async def get_my_client_job_detail(
    request: Request,
    job_id: UUID,
    db: DBDep,
    current_user: AuthenticatedClientDep,
) -> schemas.ClientJobRead:
    """Retrieve details for a specific job posted by the authenticated client."""
    job = await ClientService(db).get_job_detail(current_user.id, job_id)
    return schemas.ClientJobRead.model_validate(job, from_attributes=True)
