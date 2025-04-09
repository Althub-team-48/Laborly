"""
admin/routes.py

Defines API routes for administrative actions such as:
- Approving or rejecting KYC submissions
- Freezing, unfreezing, banning, unbanning, and deleting users
- Reviewing and moderating flagged reviews
"""

from uuid import UUID
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.services import AdminService
from app.core.dependencies import get_db, get_current_user_with_role
from app.core.limiter import limiter
from app.database.enums import UserRole
from app.database.models import User

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = logging.getLogger(__name__)


# ---------------------------
# KYC Approval/Moderation
# ---------------------------

@router.get("/kyc/pending")
@limiter.limit("10/minute")
async def get_pending_kyc_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """
    Retrieve all KYC submissions currently pending approval.
    """
    logger.info(f"[KYC] Admin {current_user.id} requested pending KYC list.")
    return await AdminService(db).list_pending_kyc()


@router.put("/kyc/{user_id}/approve")
@limiter.limit("5/minute")
async def approve_user_kyc(
    request: Request,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """
    Approve a user's submitted KYC documentation.
    """
    logger.info(f"[KYC] Admin {current_user.id} approving KYC for user {user_id}.")
    return await AdminService(db).approve_kyc(user_id)


@router.put("/kyc/{user_id}/reject")
@limiter.limit("5/minute")
async def reject_user_kyc(
    request: Request,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """
    Reject a user's submitted KYC documentation.
    """
    logger.info(f"[KYC] Admin {current_user.id} rejecting KYC for user {user_id}.")
    return await AdminService(db).reject_kyc(user_id)


# ---------------------------
# User Moderation
# ---------------------------

@router.put("/users/{user_id}/freeze")
@limiter.limit("5/minute")
async def freeze_user_account(
    request: Request,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """
    Freeze a user's account (disabling access).
    """
    logger.info(f"[USER] Admin {current_user.id} freezing user {user_id}.")
    return await AdminService(db).freeze_user(user_id)


@router.put("/users/{user_id}/unfreeze")
@limiter.limit("5/minute")
async def unfreeze_user_account(
    request: Request,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """
    Unfreeze a previously frozen user account.
    """
    logger.info(f"[USER] Admin {current_user.id} unfreezing user {user_id}.")
    return await AdminService(db).unfreeze_user(user_id)


@router.put("/users/{user_id}/ban")
@limiter.limit("5/minute")
async def ban_user_account(
    request: Request,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """
    Ban a user from the platform (disable and mark as banned).
    """
    logger.info(f"[USER] Admin {current_user.id} banning user {user_id}.")
    return await AdminService(db).ban_user(user_id)


@router.put("/users/{user_id}/unban")
@limiter.limit("5/minute")
async def unban_user_account(
    request: Request,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """
    Unban a previously banned user account.
    """
    logger.info(f"[USER] Admin {current_user.id} unbanning user {user_id}.")
    return await AdminService(db).unban_user(user_id)


@router.delete("/users/{user_id}")
@limiter.limit("3/minute")
async def delete_user_account(
    request: Request,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """
    Permanently delete a user account from the system.
    """
    logger.info(f"[USER] Admin {current_user.id} deleting user {user_id}.")
    await AdminService(db).delete_user(user_id)
    return {"detail": "User deleted successfully."}


# ---------------------------
# Review Moderation
# ---------------------------

@router.get("/reviews/flagged")
@limiter.limit("10/minute")
async def get_flagged_reviews(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """
    Get all reviews that were flagged for admin moderation.
    """
    logger.info(f"[REVIEW] Admin {current_user.id} requested flagged reviews.")
    return await AdminService(db).list_flagged_reviews()


@router.delete("/reviews/{review_id}")
@limiter.limit("5/minute")
async def delete_flagged_review(
    request: Request,
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.ADMIN)),
):
    """
    Delete a flagged review from the system.
    """
    logger.info(f"[REVIEW] Admin {current_user.id} deleting review {review_id}.")
    await AdminService(db).delete_review(review_id)
    return {"detail": "Review deleted."}
