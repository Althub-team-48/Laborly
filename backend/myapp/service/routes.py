"""
backend/app/service/routes.py

Service Routes
Defines API routes for managing worker service listings:
- Create, update, and delete services (authenticated worker or admin)
- View authenticated worker's services
- Public service search and public service detail retrieval
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from myapp.service import schemas
from myapp.service.schemas import MessageResponse, ServiceRead
from myapp.service.services import ServiceListingService
from myapp.database.enums import UserRole
from myapp.database.models import User
from myapp.database.session import get_db
from myapp.core.dependencies import get_current_user_with_role, require_roles, PaginationParams
from myapp.core.schemas import PaginatedResponse

router = APIRouter(prefix="/services", tags=["Services"])

DBDep = Annotated[AsyncSession, Depends(get_db)]
AuthenticatedWorkerAdminDep = Annotated[
    User, Depends(require_roles(UserRole.WORKER, UserRole.ADMIN))
]
AuthenticatedWorkerDep = Annotated[User, Depends(get_current_user_with_role(UserRole.WORKER))]


# ----------------------------------------------------
# Public Service Endpoints
# ----------------------------------------------------
@router.get(
    "/search",
    response_model=PaginatedResponse[schemas.ServiceRead],
    status_code=status.HTTP_200_OK,
    summary="Search Services",
    description="Search public service listings by title and/or location.",
)
async def search_services(
    request: Request,
    db: DBDep,
    title: str | None = Query(default=None, description="Filter by service title"),
    location: str | None = Query(default=None, description="Filter by service location"),
    pagination: PaginationParams = Depends(),
) -> PaginatedResponse[schemas.ServiceRead]:
    """Search publicly available services by title and/or location with pagination."""
    services, total_count = await ServiceListingService(db).search_services(
        title=title, location=location, skip=pagination.skip, limit=pagination.limit
    )
    return PaginatedResponse(
        total_count=total_count,
        has_next_page=(pagination.skip + pagination.limit) < total_count,
        items=[
            schemas.ServiceRead.model_validate(service, from_attributes=True)
            for service in services
        ],
    )


@router.get(
    "/{service_id}/public",
    response_model=ServiceRead,
    status_code=status.HTTP_200_OK,
    summary="Get Public Service Detail",
    description="Retrieve detailed information for a specific public service listing.",
)
async def get_public_service_detail(
    request: Request,
    service_id: UUID,
    db: DBDep,
) -> ServiceRead:
    """Retrieve public details for a specific service listing by ID."""
    service = await ServiceListingService(db).get_public_service_detail(service_id)
    return ServiceRead.model_validate(service, from_attributes=True)


# ----------------------------------------------------
# Authenticated Service Endpoints (Worker/Admin)
# ----------------------------------------------------
@router.post(
    "",
    response_model=schemas.ServiceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create New Service",
    description="Create a new service listing (authenticated worker or admin only).",
)
async def create_service(
    request: Request,
    data: schemas.ServiceCreate,
    db: DBDep,
    current_user: AuthenticatedWorkerAdminDep,
) -> schemas.ServiceRead:
    """Create a new service listing."""
    service = await ServiceListingService(db).create_service(current_user.id, data)
    return schemas.ServiceRead.model_validate(service, from_attributes=True)


@router.put(
    "/{service_id}",
    response_model=schemas.ServiceRead,
    status_code=status.HTTP_200_OK,
    summary="Update Service",
    description="Update an existing service listing (authenticated worker or admin only).",
)
async def update_service(
    request: Request,
    service_id: UUID,
    data: schemas.ServiceUpdate,
    db: DBDep,
    current_user: AuthenticatedWorkerAdminDep,
) -> schemas.ServiceRead:
    """Update an existing service listing."""
    service = await ServiceListingService(db).update_service(current_user.id, service_id, data)
    return schemas.ServiceRead.model_validate(service, from_attributes=True)


@router.delete(
    "/{service_id}",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponse,
    summary="Delete Service",
    description="Delete an existing service listing (authenticated worker or admin only).",
)
async def delete_service(
    request: Request,
    service_id: UUID,
    db: DBDep,
    current_user: AuthenticatedWorkerAdminDep,
) -> MessageResponse:
    """Delete an existing service listing."""
    await ServiceListingService(db).delete_service(current_user.id, service_id)
    return MessageResponse(detail="Service deleted successfully")


@router.get(
    "/my",
    response_model=PaginatedResponse[schemas.ServiceRead],
    status_code=status.HTTP_200_OK,
    summary="List My Services",
    description="List all services created by the authenticated worker.",
)
async def list_my_services(
    request: Request,
    db: DBDep,
    current_user: AuthenticatedWorkerDep,
    pagination: PaginationParams = Depends(),
) -> PaginatedResponse[schemas.ServiceRead]:
    """List all services created by the authenticated worker with pagination."""
    services, total_count = await ServiceListingService(db).get_my_services(
        current_user.id, skip=pagination.skip, limit=pagination.limit
    )
    return PaginatedResponse(
        total_count=total_count,
        has_next_page=(pagination.skip + pagination.limit) < total_count,
        items=[
            schemas.ServiceRead.model_validate(service, from_attributes=True)
            for service in services
        ],
    )
