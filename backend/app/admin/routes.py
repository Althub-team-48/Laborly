"""
[admin] routes.py

Defines admin-only routes for managing:
- Users (verification)
- Jobs (overview)
- Disputes (resolution)
"""

from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from admin.schemas import (
    DisputeUpdate, DisputeOut, DisputeList,
    UserList, JobList, UserOut
)
from admin.service import AdminService
from core.dependencies import get_db, get_admin_user
from core.exceptions import APIError

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"],
    dependencies=[Depends(get_admin_user)]
)


@router.get("/users/", response_model=UserList, responses={
    200: {"description": "List of all users"},
})
def list_users(db: Session = Depends(get_db)):
    """List all registered users (admin-only)."""
    return {"users": AdminService.get_users(db)}


@router.patch("/verify/{user_id}", response_model=UserOut, responses={
    200: {"description": "User verification status updated"},
    404: {"description": "User not found"}
})
def update_user_verification(
    user_id: int,
    is_verified: bool,
    db: Session = Depends(get_db)
):
    """Update a user's verification status (admin-only)."""
    try:
        return AdminService.update_user_verification(db, user_id, is_verified)
    except ValueError as e:
        raise APIError(status_code=404, message=str(e))


@router.get("/jobs/", response_model=JobList, responses={
    200: {"description": "List of all jobs"},
})
def list_jobs(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all jobs, optionally filtered by status (admin-only)."""
    return {"jobs": AdminService.get_jobs(db, status)}


@router.get("/disputes/", response_model=DisputeList, responses={
    200: {"description": "List of all disputes"},
})
def list_disputes(db: Session = Depends(get_db)):
    """Retrieve all unresolved/resolved disputes (admin-only)."""
    return {"disputes": AdminService.get_disputes(db)}


@router.patch("/dispute/resolve/{dispute_id}", response_model=DisputeOut, responses={
    200: {"description": "Dispute resolved successfully"},
    404: {"description": "Dispute not found"},
})
def resolve_dispute(
    dispute_id: int,
    update: DisputeUpdate,
    db: Session = Depends(get_db)
):
    """Resolve a dispute and optionally update job status (admin-only)."""
    try:
        return AdminService.resolve_dispute(db, dispute_id, update)
    except ValueError as e:
        raise APIError(status_code=404, message=str(e))
