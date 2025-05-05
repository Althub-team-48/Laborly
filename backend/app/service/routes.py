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

from app.service import schemas
from app.service.schemas import ServiceRead

from app.core.schemas import MessageResponse, PaginatedResponse

from app.service.services import ServiceListingService
from app.database.enums import UserRole
from app.database.models import User
from app.database.session import get_db
from app.core.dependencies import get_current_user_with_role, require_roles, PaginationParams
from app.core.limiter import limiter

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
    response_model=PaginatedResponse[ServiceRead],
    status_code=status.HTTP_200_OK,
    summary="Search Services",
    description="Search public service listings by title and/or location.",
)
@limiter.limit("30/minute")
async def search_services(
    request: Request,
    db: DBDep,
    title: str | None = Query(
        default=None, description="Filter by service title (case-insensitive)"
    ),
    location: str | None = Query(
        default=None, description="Filter by service location (case-insensitive)"
    ),
    pagination: PaginationParams = Depends(),
) -> PaginatedResponse[ServiceRead]:
    """Search publicly available services by title and/or location with pagination."""
    # Service returns tuple[list[ServiceRead], int]
    services_list, total_count = await ServiceListingService(db).search_services(
        title=title, location=location, skip=pagination.skip, limit=pagination.limit
    )
    return PaginatedResponse(
        total_count=total_count,
        has_next_page=(pagination.skip + pagination.limit) < total_count,
        items=services_list,
    )


@router.get(
    "/{service_id}/public",
    response_model=ServiceRead,
    status_code=status.HTTP_200_OK,
    summary="Get Public Service Detail",
    description="Retrieve detailed information for a specific public service listing.",
)
@limiter.limit("30/minute")
async def get_public_service_detail(
    request: Request,
    service_id: UUID,
    db: DBDep,
) -> ServiceRead:
    """Retrieve public details for a specific service listing by ID."""
    # Service returns ServiceRead
    return await ServiceListingService(db).get_public_service_detail(service_id)


# ----------------------------------------------------
# Authenticated Service Endpoints (Worker/Admin)
# ----------------------------------------------------
@router.post(
    "",
    response_model=ServiceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create New Service",
    description="Create a new service listing (authenticated worker or admin only).",
)
@limiter.limit("10/minute")
async def create_service(
    request: Request,
    data: schemas.ServiceCreate,
    db: DBDep,
    current_user: AuthenticatedWorkerAdminDep,
) -> ServiceRead:
    """Create a new service listing."""
    return await ServiceListingService(db).create_service(current_user.id, data)


@router.put(
    "/{service_id}",
    response_model=ServiceRead,
    status_code=status.HTTP_200_OK,
    summary="Update Service",
    description="Update an existing service listing (authenticated worker or admin only).",
)
@limiter.limit("10/minute")
async def update_service(
    request: Request,
    service_id: UUID,
    data: schemas.ServiceUpdate,
    db: DBDep,
    current_user: AuthenticatedWorkerAdminDep,
) -> ServiceRead:
    """Update an existing service listing."""
    return await ServiceListingService(db).update_service(current_user.id, service_id, data)


@router.delete(
    "/{service_id}",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponse,
    summary="Delete Service",
    description="Delete an existing service listing (authenticated worker or admin only).",
)
@limiter.limit("5/minute")
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
    response_model=PaginatedResponse[ServiceRead],
    status_code=status.HTTP_200_OK,
    summary="List My Services",
    description="List all services created by the authenticated worker.",
)
@limiter.limit("10/minute")
async def list_my_services(
    request: Request,
    db: DBDep,
    current_user: AuthenticatedWorkerDep,
    pagination: PaginationParams = Depends(),
) -> PaginatedResponse[ServiceRead]:
    """List all services created by the authenticated worker with pagination."""
    services_list, total_count = await ServiceListingService(db).get_my_services(
        current_user.id, skip=pagination.skip, limit=pagination.limit
    )
    return PaginatedResponse(
        total_count=total_count,
        has_next_page=(pagination.skip + pagination.limit) < total_count,
        items=services_list,
    )
