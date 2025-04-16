"""
client/routes.py

Defines routes under the Client module for:
- Profile management
- Favorite worker handling
- Client job history and job details
"""

from uuid import UUID
from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.client.services import ClientService
from app.client import schemas
from app.core.dependencies import get_db, require_roles
from app.database.models import User, UserRole
from app.core.limiter import limiter

router = APIRouter(prefix="/client", tags=["Client"])


# ----------------------------------------
# Client Profile Endpoints
# ----------------------------------------

client_user_dependency=require_roles(UserRole.CLIENT, UserRole.ADMIN)

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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(client_user_dependency),
):
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(client_user_dependency),
):
    return await ClientService(db).update_profile(current_user.id, data)


# ----------------------------------------
# Favorite Workers Endpoints
# ----------------------------------------

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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(client_user_dependency),
):
    return await ClientService(db).list_favorites(current_user.id)


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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(client_user_dependency),
):
    return await ClientService(db).add_favorite(current_user.id, worker_id)


@router.delete(
    "/delete/favorites/{worker_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove Favorite Worker",
    description="Remove a worker from the client's list of favorites.",
)
@limiter.limit("5/minute")
async def remove_favorite_worker(
    request: Request,
    worker_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(client_user_dependency),
):
    await ClientService(db).remove_favorite(current_user.id, worker_id)
    return


# ----------------------------------------
# Job History Endpoints
# ----------------------------------------

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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(client_user_dependency),
):
    return await ClientService(db).get_jobs(current_user.id)


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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(client_user_dependency),
):
    return await ClientService(db).get_job_detail(current_user.id, job_id)
