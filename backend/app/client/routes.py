"""
client/routes.py

Defines routes under the Client module for:
- Profile management
- Favorite worker handling
- Client job history and job details
"""

from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.client import schemas
from app.client.schemas import MessageResponse
from app.client.services import ClientService
from app.core.dependencies import get_db, require_roles
from app.core.limiter import limiter
from app.database.enums import UserRole
from app.database.models import User

# ---------------------------------------------------
# Router Configuration
# ---------------------------------------------------
router = APIRouter(prefix="/client", tags=["Client"])

# ---------------------------------------------------
# Dependencies
# ---------------------------------------------------
UserDep = Annotated[User, Depends(require_roles(UserRole.CLIENT, UserRole.ADMIN))]
DBDep = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------
# Client Profile Endpoints
# ---------------------------------------------------
@router.get(
    "/get/profile",
    response_model=schemas.ClientProfileRead,
    status_code=status.HTTP_200_OK,
    summary="Get Client Profile",
    description="Retrieve the profile of the currently authenticated client user.",
)
@limiter.limit("10/minute")
async def get_client_profile(
    request: Request,
    db: DBDep,
    current_user: UserDep,
) -> schemas.ClientProfileRead:
    """
    Retrieves the client profile for the authenticated user.
    """
    return await ClientService(db).get_profile(current_user.id)


@router.patch(
    "/update/profile",
    response_model=schemas.ClientProfileRead,
    status_code=status.HTTP_200_OK,
    summary="Update Client Profile",
    description="Update fields in the authenticated client's profile.",
)
@limiter.limit("5/minute")
async def update_client_profile(
    request: Request,
    data: schemas.ClientProfileUpdate,
    db: DBDep,
    current_user: UserDep,
) -> schemas.ClientProfileRead:
    """
    Updates the client profile for the authenticated user.
    """
    return await ClientService(db).update_profile(current_user.id, data)


# ---------------------------------------------------
# Favorite Workers Endpoints
# ---------------------------------------------------
@router.get(
    "/get/favorites",
    response_model=list[schemas.FavoriteRead],
    status_code=status.HTTP_200_OK,
    summary="List Favorite Workers",
    description="Retrieve a list of workers the client has marked as favorites.",
)
@limiter.limit("10/minute")
async def list_favorite_workers(
    request: Request,
    db: DBDep,
    current_user: UserDep,
) -> list[schemas.FavoriteRead]:
    """
    Retrieves a list of the client's favorite workers.
    """
    favorites = await ClientService(db).list_favorites(current_user.id)
    return [schemas.FavoriteRead.model_validate(fav) for fav in favorites]


@router.post(
    "/add/favorites/{worker_id}",
    response_model=schemas.FavoriteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add Favorite Worker",
    description="Add a specific worker to the client's list of favorites.",
)
@limiter.limit("5/minute")
async def add_favorite_worker(
    request: Request,
    worker_id: UUID,
    db: DBDep,
    current_user: UserDep,
) -> schemas.FavoriteRead:
    """
    Adds a worker to the client's favorite list.
    """
    fav = await ClientService(db).add_favorite(current_user.id, worker_id)
    return schemas.FavoriteRead.model_validate(fav)


@router.delete(
    "/delete/favorites/{worker_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove Favorite Worker",
    description="Remove a worker from the client's list of favorites.",
)
@limiter.limit("5/minute")
async def remove_favorite_worker(
    request: Request,
    worker_id: UUID,
    db: DBDep,
    current_user: UserDep,
) -> MessageResponse:
    """
    Removes a worker from the client's favorite list.
    """
    await ClientService(db).remove_favorite(current_user.id, worker_id)
    return MessageResponse(detail="Favorite worker removed successfully.")


# ---------------------------------------------------
# Job History Endpoints
# ---------------------------------------------------
@router.get(
    "/list/jobs",
    response_model=list[schemas.ClientJobRead],
    status_code=status.HTTP_200_OK,
    summary="List Client Jobs",
    description="List all jobs created by the client user.",
)
@limiter.limit("10/minute")
async def list_client_jobs(
    request: Request,
    db: DBDep,
    current_user: UserDep,
) -> list[schemas.ClientJobRead]:
    """
    Retrieves a list of jobs created by the client.
    """
    jobs = await ClientService(db).get_jobs(current_user.id)
    return [schemas.ClientJobRead.model_validate(job) for job in jobs]


@router.get(
    "/get/jobs/{job_id}",
    response_model=schemas.ClientJobRead,
    status_code=status.HTTP_200_OK,
    summary="Get Job Detail",
    description="Get detailed information for a specific job posted by the client.",
)
@limiter.limit("10/minute")
async def get_client_job_detail(
    request: Request,
    job_id: UUID,
    db: DBDep,
    current_user: UserDep,
) -> schemas.ClientJobRead:
    """
    Retrieves detailed information for a specific job created by the client.
    """
    job = await ClientService(db).get_job_detail(current_user.id, job_id)
    return schemas.ClientJobRead.model_validate(job)
