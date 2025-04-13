"""
service/routes.py

Defines routes for managing worker service listings:
- Create, update, and delete services
- View authenticated worker’s services
- Public service search by title/location
"""

from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.service import schemas
from app.service.services import ServiceListingService
from app.database.session import get_db
from app.core.dependencies import require_roles
from app.database.models import User, UserRole

router = APIRouter(prefix="/services", tags=["Services"])


# --------------------------------------------------
# Create a new service listing (Worker or Admin)
# --------------------------------------------------
@router.post("", response_model=schemas.ServiceRead)
def create_service(
    data: schemas.ServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.WORKER, UserRole.ADMIN)),
):
    """
    Create a new service listing for the authenticated worker.
    """
    return ServiceListingService(db).create_service(current_user.id, data)


# --------------------------------------------------
# Update an existing service (Worker or Admin)
# --------------------------------------------------
@router.put("/{service_id}", response_model=schemas.ServiceRead)
def update_service(
    service_id: UUID,
    data: schemas.ServiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.WORKER, UserRole.ADMIN)),
):
    """
    Update a service listing owned by the authenticated worker.
    """
    return ServiceListingService(db).update_service(current_user.id, service_id, data)


# --------------------------------------------------
# Delete a service listing (Worker or Admin)
# --------------------------------------------------
@router.delete("/{service_id}")
def delete_service(
    service_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.WORKER, UserRole.ADMIN)),
):
    """
    Delete a service listing owned by the authenticated worker.
    """
    ServiceListingService(db).delete_service(current_user.id, service_id)
    return {"detail": "Service deleted successfully"}


# --------------------------------------------------
# List all services by current authenticated user
# --------------------------------------------------
@router.get("/my", response_model=List[schemas.ServiceRead])
def list_my_services(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.WORKER, UserRole.ADMIN)),
):
    """
    Get all services created by the authenticated worker.
    """
    return ServiceListingService(db).get_my_services(current_user.id)


# --------------------------------------------------
# Public search for services (No login required)
# --------------------------------------------------
@router.get("/search", response_model=List[schemas.ServiceRead])
def search_services(
    title: Optional[str] = Query(default=None, description="Filter by service title"),
    location: Optional[str] = Query(default=None, description="Filter by service location"),
    db: Session = Depends(get_db),
):
    """
    Public search endpoint to find services by title and/or location.
    """
    return ServiceListingService(db).search_services(title=title, location=location)
