"""
service/routes.py

Defines routes for managing worker service listings:
- Create, update, and delete services
- View authenticated worker’s services
- Public service search by title/location
"""

from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.service import schemas
from app.service.services import ServiceListingService
from app.database.session import get_db
from app.core.dependencies import require_roles
from app.database.models import User, UserRole

router = APIRouter(prefix="/services", tags=["Services"])

require_worker_admin_roles = require_roles(UserRole.WORKER, UserRole.ADMIN)

# ---------------------------
# Create Service
# ---------------------------
@router.post(
    "",
    response_model=schemas.ServiceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create New Service",
    description="Create a new service listing. Only workers and admins can perform this action."
)
async def create_service(
    request: Request,
    data: schemas.ServiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_worker_admin_roles),
):
    return await ServiceListingService(db).create_service(current_user.id, data)


# ---------------------------
# Update Service
# ---------------------------
@router.put(
    "/{service_id}",
    response_model=schemas.ServiceRead,
    status_code=status.HTTP_200_OK,
    summary="Update Service",
    description="Update an existing service. Only the owner (worker) or admin can update."
)
async def update_service(
    request: Request,
    service_id: UUID,
    data: schemas.ServiceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_worker_admin_roles),
):
    return await ServiceListingService(db).update_service(current_user.id, service_id, data)


# ---------------------------
# Delete Service
# ---------------------------
@router.delete(
    "/{service_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Service",
    description="Delete an existing service. Only the owner (worker) or admin can delete."
)
async def delete_service(
    request: Request,
    service_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_worker_admin_roles),
):
    await ServiceListingService(db).delete_service(current_user.id, service_id)
    return {"detail": "Service deleted successfully"}


# ---------------------------
# List My Services
# ---------------------------
@router.get(
    "/my",
    response_model=List[schemas.ServiceRead],
    status_code=status.HTTP_200_OK,
    summary="List My Services",
    description="Returns all services created by the authenticated worker or admin."
)
async def list_my_services(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_worker_admin_roles),
):
    return await ServiceListingService(db).get_my_services(current_user.id)


# ---------------------------
# Search Public Services
# ---------------------------
@router.get(
    "/search",
    response_model=List[schemas.ServiceRead],
    status_code=status.HTTP_200_OK,
    summary="Search Services",
    description="Search public service listings by title and/or location."
)
async def search_services(
    request: Request,
    title: Optional[str] = Query(default=None, description="Filter by service title"),
    location: Optional[str] = Query(default=None, description="Filter by service location"),
    db: AsyncSession = Depends(get_db),
):
    return await ServiceListingService(db).search_services(title=title, location=location)
