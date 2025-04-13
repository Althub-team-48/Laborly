"""
admin/routes.py

Defines routes for administrative actions:
- Approve or reject KYC submissions
- Freeze, unfreeze, ban, unban, and delete user accounts
- View and delete flagged reviews for moderation
"""

from uuid import UUID
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from main import limiter  # Using centralized limiter instance
from app.core.dependencies import get_db, get_current_user_with_role
from app.database.enums import UserRole
from app.database.models import User
from app.admin.services import AdminService

# Logger setup
logger = logging.getLogger(__name__)

# Route group
router = APIRouter(prefix="/admin", tags=["Admin"])


# -------------------------------------------------------------------
# KYC Moderation Endpoints
# -------------------------------------------------------------------

@router.get("/kyc/pending")
@limiter.limit("10/minute")
def get_pending_kyc_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """
    Retrieve a list of users with pending KYC submissions.
    """
    logger.info(f"[KYC] Admin {current_user.id} requested pending KYC list.")
    return AdminService(db).list_pending_kyc()


@router.put("/kyc/{user_id}/approve")
@limiter.limit("5/minute")
def approve_user_kyc(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """
    Approve a user's KYC submission.
    """
    logger.info(f"[KYC] Admin {current_user.id} approving KYC for user {user_id}.")
    return AdminService(db).approve_kyc(user_id)


@router.put("/kyc/{user_id}/reject")
@limiter.limit("5/minute")
def reject_user_kyc(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """
    Reject a user's KYC submission.
    """
    logger.info(f"[KYC] Admin {current_user.id} rejecting KYC for user {user_id}.")
    return AdminService(db).reject_kyc(user_id)


# -------------------------------------------------------------------
# User Management Endpoints
# -------------------------------------------------------------------

@router.put("/users/{user_id}/freeze")
@limiter.limit("5/minute")
def freeze_user_account(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """
    Freeze a user's account to temporarily disable access.
    """
    logger.info(f"[USER] Admin {current_user.id} freezing user {user_id}.")
    return AdminService(db).freeze_user(user_id)


@router.put("/users/{user_id}/unfreeze")
@limiter.limit("5/minute")
def unfreeze_user_account(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """
    Unfreeze a previously frozen user account.
    """
    logger.info(f"[USER] Admin {current_user.id} unfreezing user {user_id}.")
    return AdminService(db).unfreeze_user(user_id)


@router.put("/users/{user_id}/ban")
@limiter.limit("5/minute")
def ban_user_account(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """
    Permanently ban a user account from the system.
    """
    logger.info(f"[USER] Admin {current_user.id} banning user {user_id}.")
    return AdminService(db).ban_user(user_id)


@router.put("/users/{user_id}/unban")
@limiter.limit("5/minute")
def unban_user_account(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """
    Reinstate a previously banned user account.
    """
    logger.info(f"[USER] Admin {current_user.id} unbanning user {user_id}.")
    return AdminService(db).unban_user(user_id)


@router.delete("/users/{user_id}")
@limiter.limit("3/minute")
def delete_user_account(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """
    Permanently delete a user account from the system.
    """
    logger.info(f"[USER] Admin {current_user.id} deleting user {user_id}.")
    AdminService(db).delete_user(user_id)
    return {"detail": "User deleted successfully."}


# -------------------------------------------------------------------
# Review Moderation Endpoints
# -------------------------------------------------------------------

@router.get("/reviews/flagged")
@limiter.limit("10/minute")
def get_flagged_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """
    Retrieve all reviews that have been flagged for moderation.
    """
    logger.info(f"[REVIEW] Admin {current_user.id} requested flagged reviews.")
    return AdminService(db).list_flagged_reviews()


@router.delete("/reviews/{review_id}")
@limiter.limit("5/minute")
def delete_flagged_review(
    review_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """
    Delete a specific review flagged for moderation.
    """
    logger.info(f"[REVIEW] Admin {current_user.id} deleting review {review_id}.")
    AdminService(db).delete_review(review_id)
    return {"detail": "Review deleted."}
