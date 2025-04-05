"""
client/routes.py

Client module routes for:
- Profile management
- Favorite worker management
- Job history and job detail access
"""

from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.client.services import ClientService
from app.client import schemas
from app.core.dependencies import get_db, require_roles
from app.database.models import User, UserRole

router = APIRouter(prefix="/client", tags=["Client"])

# -------------------------------
# Client Profile Management
# -------------------------------

@router.get("/get/profile", response_model=schemas.ClientProfileRead)
def get_client_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CLIENT, UserRole.ADMIN)),
):
    """
    Retrieve the profile of the authenticated client.
    """
    return ClientService(db).get_profile(current_user.id)


@router.patch("/update/profile", response_model=schemas.ClientProfileRead)
def update_client_profile(
    data: schemas.ClientProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CLIENT, UserRole.ADMIN)),
):
    """
    Update the authenticated client’s profile.
    """
    return ClientService(db).update_profile(current_user.id, data)

# -------------------------------
# Favorite Worker Management
# -------------------------------

@router.get("/get/favorites", response_model=list[schemas.FavoriteRead])
def list_favorite_workers(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CLIENT, UserRole.ADMIN)),
):
    """
    List all favorite workers of the authenticated client.
    """
    return ClientService(db).list_favorites(current_user.id)


@router.post("/add/favorites/{worker_id}", response_model=schemas.FavoriteRead)
def add_favorite_worker(
    worker_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CLIENT, UserRole.ADMIN)),
):
    """
    Add a worker to the authenticated client’s favorites.
    """
    return ClientService(db).add_favorite(current_user.id, worker_id)


@router.delete("/delete/favorites/{worker_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite_worker(
    worker_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CLIENT, UserRole.ADMIN)),
):
    """
    Remove a worker from the authenticated client’s favorites.
    """
    ClientService(db).remove_favorite(current_user.id, worker_id)
    return

# -------------------------------
# Job History and Detail
# -------------------------------

@router.get("/list/jobs", response_model=list[schemas.ClientJobRead])
def list_client_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CLIENT, UserRole.ADMIN)),
):
    """
    List all jobs associated with the authenticated client.
    """
    return ClientService(db).get_jobs(current_user.id)


@router.get("/get/jobs/{job_id}", response_model=schemas.ClientJobRead)
def get_client_job_detail(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CLIENT, UserRole.ADMIN)),
):
    """
    Retrieve detailed information for a specific job by the client.
    """
    return ClientService(db).get_job_detail(current_user.id, job_id)
