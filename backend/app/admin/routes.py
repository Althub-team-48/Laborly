"""
admin/routes.py

Defines API routes for administrative actions such as:
- Approving or rejecting KYC submissions
- Freezing, unfreezing, banning, unbanning, and deleting users
- Reviewing and moderating flagged reviews
"""

import logging
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import HttpUrl, TypeAdapter, ValidationError


from app.admin.schemas import (
    KYCPendingListItem,
    KYCDetailAdminView,
    KYCReviewActionResponse,
    UserStatusUpdateResponse,
    FlaggedReviewRead,
    MessageResponse,
    PresignedUrlResponse,
)
from app.admin.services import AdminService
from app.core.dependencies import get_current_user_with_role, get_db
from app.core.limiter import limiter
from app.database.enums import UserRole
from app.database.models import User

# ---------------------------------------------------
# Router Configuration
# ---------------------------------------------------
router = APIRouter(prefix="/admin", tags=["Admin"])
logger = logging.getLogger(__name__)

# ---------------------------------------------------
# Dependencies
# ---------------------------------------------------
DBDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[User, Depends(get_current_user_with_role(UserRole.ADMIN))]


# ---------------------------------------------------
# Helper Functions
# ---------------------------------------------------
def build_status_response(user_id: UUID, action: str) -> UserStatusUpdateResponse:
    """Builds a standard response for user status update actions."""
    return UserStatusUpdateResponse(
        user_id=user_id,
        action=action,
        success=True,
        timestamp=datetime.now(timezone.utc),
    )


# ---------------------------------------------------
# KYC Endpoints
# ---------------------------------------------------
@router.get(
    "/kyc/pending",
    response_model=list[KYCPendingListItem],
    status_code=status.HTTP_200_OK,
    summary="List Pending KYC Submissions",
    description="Retrieves a list of users with pending KYC submissions, including document type and submission time.",
)
@limiter.limit("10/minute")
async def get_pending_kyc_list(
    request: Request,
    db: DBDep,
    current_user: AdminDep,
) -> list[KYCPendingListItem]:
    """
    Retrieves a list of users with pending KYC submissions.
    """
    logger.info(f"[KYC] Admin {current_user.id} requested pending KYC list.")
    pending_kyc_models = await AdminService(db).list_pending_kyc()
    return [
        KYCPendingListItem.model_validate(kyc, from_attributes=True) for kyc in pending_kyc_models
    ]


@router.get(
    "/kyc/{user_id}",
    response_model=KYCDetailAdminView,
    status_code=status.HTTP_200_OK,
    summary="Get Specific KYC Details",
    description="Retrieves detailed information about a specific user's KYC submission.",
)
@limiter.limit("15/minute")
async def get_kyc_details(
    request: Request,
    user_id: UUID,
    db: DBDep,
    current_user: AdminDep,
) -> KYCDetailAdminView:
    """
    Retrieves detailed KYC information for a specific user.
    """
    logger.info(f"[KYC] Admin {current_user.id} requesting details for user {user_id}.")
    kyc_model = await AdminService(db).get_kyc_details_for_admin(user_id)
    return KYCDetailAdminView.model_validate(kyc_model, from_attributes=True)


@router.put(
    "/kyc/{user_id}/approve",
    response_model=KYCReviewActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve KYC Submission",
    description="Approves the KYC submission for a specific user.",
)
@limiter.limit("5/minute")
async def approve_user_kyc(
    request: Request,
    user_id: UUID,
    db: DBDep,
    current_user: AdminDep,
) -> KYCReviewActionResponse:
    """
    Approves the KYC submission for a specific user.
    """
    logger.info(f"[KYC] Admin {current_user.id} approving KYC for user {user_id}.")
    updated_kyc_model = await AdminService(db).approve_kyc(user_id)
    return KYCReviewActionResponse.model_validate(updated_kyc_model, from_attributes=True)


@router.put(
    "/kyc/{user_id}/reject",
    response_model=KYCReviewActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject KYC Submission",
    description="Rejects the KYC submission for a specific user.",
)
@limiter.limit("5/minute")
async def reject_user_kyc(
    request: Request,
    user_id: UUID,
    db: DBDep,
    current_user: AdminDep,
) -> KYCReviewActionResponse:
    """
    Rejects the KYC submission for a specific user.
    """
    logger.info(f"[KYC] Admin {current_user.id} rejecting KYC for user {user_id}.")
    updated_kyc_model = await AdminService(db).reject_kyc(user_id)
    return KYCReviewActionResponse.model_validate(updated_kyc_model, from_attributes=True)


@router.get(
    "/kyc/{user_id}/presigned-url/{doc_type}",
    response_model=PresignedUrlResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Pre-signed URL for KYC Document",
    description="Generates a temporary, secure URL for an admin to view a specific KYC document (document or selfie).",
)
@limiter.limit("20/minute")
async def get_kyc_document_presigned_url(
    request: Request,
    user_id: UUID,
    doc_type: Literal["document", "selfie"],
    db: DBDep,
    current_user: AdminDep,
) -> PresignedUrlResponse:
    """
    Generates a pre-signed URL for viewing a specific KYC document.
    Requires admin privileges.
    """
    logger.info(
        f"Admin {current_user.id} requesting pre-signed URL for user {user_id}, doc_type: {doc_type}"
    )

    admin_service = AdminService(db)
    generated_url = await admin_service.get_kyc_presigned_url(user_id=user_id, doc_type=doc_type)

    try:
        validated_url = TypeAdapter(HttpUrl).validate_python(generated_url)
    except ValidationError as e:
        logger.error(f"URL validation failed for generated presigned URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate a valid pre-signed URL.",
        )

    return PresignedUrlResponse(url=validated_url)


# ---------------------------------------------------
# User Management Endpoints
# ---------------------------------------------------
@router.put("/users/{user_id}/freeze", response_model=UserStatusUpdateResponse)
@limiter.limit("5/minute")
async def freeze_user_account(
    request: Request,
    user_id: UUID,
    db: DBDep,
    current_user: AdminDep,
) -> UserStatusUpdateResponse:
    logger.info(f"[USER] Admin {current_user.id} freezing user {user_id}.")
    await AdminService(db).freeze_user(user_id)
    return build_status_response(user_id, "frozen")


@router.put("/users/{user_id}/unfreeze", response_model=UserStatusUpdateResponse)
@limiter.limit("5/minute")
async def unfreeze_user_account(
    request: Request,
    user_id: UUID,
    db: DBDep,
    current_user: AdminDep,
) -> UserStatusUpdateResponse:
    logger.info(f"[USER] Admin {current_user.id} unfreezing user {user_id}.")
    await AdminService(db).unfreeze_user(user_id)
    return build_status_response(user_id, "unfrozen")


@router.put("/users/{user_id}/ban", response_model=UserStatusUpdateResponse)
@limiter.limit("5/minute")
async def ban_user_account(
    request: Request,
    user_id: UUID,
    db: DBDep,
    current_user: AdminDep,
) -> UserStatusUpdateResponse:
    logger.info(f"[USER] Admin {current_user.id} banning user {user_id}.")
    await AdminService(db).ban_user(user_id)
    return build_status_response(user_id, "banned")


@router.put("/users/{user_id}/unban", response_model=UserStatusUpdateResponse)
@limiter.limit("5/minute")
async def unban_user_account(
    request: Request,
    user_id: UUID,
    db: DBDep,
    current_user: AdminDep,
) -> UserStatusUpdateResponse:
    logger.info(f"[USER] Admin {current_user.id} unbanning user {user_id}.")
    await AdminService(db).unban_user(user_id)
    return build_status_response(user_id, "unbanned")


@router.delete("/users/{user_id}", response_model=UserStatusUpdateResponse)
@limiter.limit("3/minute")
async def delete_user_account(
    request: Request,
    user_id: UUID,
    db: DBDep,
    current_user: AdminDep,
) -> UserStatusUpdateResponse:
    """
    Soft deletes a specific user's account.
    """
    logger.info(f"[USER] Admin {current_user.id} soft deleting user {user_id}.")
    await AdminService(db).delete_user(user_id)
    return build_status_response(user_id, "deleted")


# ---------------------------------------------------
# Review Management Endpoints
# ---------------------------------------------------
@router.get("/reviews/flagged", response_model=list[FlaggedReviewRead])
@limiter.limit("10/minute")
async def get_flagged_reviews(
    request: Request,
    db: DBDep,
    current_user: AdminDep,
) -> list[FlaggedReviewRead]:
    logger.info(f"[REVIEW] Admin {current_user.id} requested flagged reviews.")
    reviews = await AdminService(db).list_flagged_reviews()
    return [FlaggedReviewRead.model_validate(review, from_attributes=True) for review in reviews]


@router.delete("/reviews/{review_id}", response_model=MessageResponse)
@limiter.limit("5/minute")
async def delete_flagged_review(
    request: Request,
    review_id: UUID,
    db: DBDep,
    current_user: AdminDep,
) -> MessageResponse:
    logger.info(f"[REVIEW] Admin {current_user.id} deleting review {review_id}.")
    await AdminService(db).delete_review(review_id)
    return MessageResponse(detail="Review deleted.")
