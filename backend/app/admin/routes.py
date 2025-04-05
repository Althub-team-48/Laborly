"""
admin/routes.py

Defines routes for administrative actions:
- KYC approval and rejection
- User freeze/ban/unban/delete
- Flagged review moderation
"""

from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import logging

from app.core.dependencies import get_db, get_current_user_with_role
from app.database.enums import UserRole
from app.database.models import User
from app.admin.services import AdminService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


# -------------------------------------------
# KYC Moderation Endpoints
# -------------------------------------------
@router.get("/kyc/pending")
def get_pending_kyc_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """List all users with pending KYC submissions."""
    logger.info(f"[KYC] Admin {current_user.id} requested pending KYC list.")
    return AdminService(db).list_pending_kyc()


@router.put("/kyc/{user_id}/approve")
def approve_user_kyc(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """Approve KYC submission for a given user."""
    logger.info(f"[KYC] Admin {current_user.id} approving KYC for user {user_id}.")
    return AdminService(db).approve_kyc(user_id)


@router.put("/kyc/{user_id}/reject")
def reject_user_kyc(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """Reject KYC submission for a given user."""
    logger.info(f"[KYC] Admin {current_user.id} rejecting KYC for user {user_id}.")
    return AdminService(db).reject_kyc(user_id)


# -------------------------------------------
# User Management Endpoints
# -------------------------------------------
@router.put("/users/{user_id}/freeze")
def freeze_user_account(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """Freeze a user's account (temporarily disables access)."""
    logger.info(f"[USER] Admin {current_user.id} freezing user {user_id}.")
    return AdminService(db).freeze_user(user_id)


@router.put("/users/{user_id}/unfreeze")
def unfreeze_user_account(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """Unfreeze a previously frozen user account."""
    logger.info(f"[USER] Admin {current_user.id} unfreezing user {user_id}.")
    return AdminService(db).unfreeze_user(user_id)


@router.put("/users/{user_id}/ban")
def ban_user_account(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """Permanently ban a user account."""
    logger.info(f"[USER] Admin {current_user.id} banning user {user_id}.")
    return AdminService(db).ban_user(user_id)


@router.put("/users/{user_id}/unban")
def unban_user_account(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """Reinstate a previously banned user account."""
    logger.info(f"[USER] Admin {current_user.id} unbanning user {user_id}.")
    return AdminService(db).unban_user(user_id)


@router.delete("/users/{user_id}")
def delete_user_account(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """Delete a user account from the system."""
    logger.info(f"[USER] Admin {current_user.id} deleting user {user_id}.")
    AdminService(db).delete_user(user_id)
    return {"detail": "User deleted successfully."}


# -------------------------------------------
# Review Moderation Endpoints
# -------------------------------------------
@router.get("/reviews/flagged")
def get_flagged_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """List all reviews flagged for moderation."""
    logger.info(f"[REVIEW] Admin {current_user.id} requested flagged reviews.")
    return AdminService(db).list_flagged_reviews()


@router.delete("/reviews/{review_id}")
def delete_flagged_review(
    review_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """Delete a specific flagged review."""
    logger.info(f"[REVIEW] Admin {current_user.id} deleting review {review_id}.")
    AdminService(db).delete_review(review_id)
    return {"detail": "Review deleted."}
