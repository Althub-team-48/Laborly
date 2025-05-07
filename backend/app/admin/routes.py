"""
backend/app/admin/routes.py

Admin API Routes

Defines routes for administrative operations including:
- Managing KYC submissions (approve/reject)
- Accessing KYC documents securely
- Updating user statuses (freeze, unfreeze, ban, unban, delete)
- Listing and viewing users with filtering and pagination
- Reviewing and moderating flagged reviews

All endpoints require Admin authentication.
"""

import logging
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import HttpUrl, TypeAdapter, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.schemas import (
    AdminUserView,
    FlaggedReviewRead,
    KYCDetailAdminView,
    KYCPendingListItem,
    KYCReviewActionResponse,
    PresignedUrlResponse,
    UserStatusUpdateResponse,
)
from app.core.schemas import PaginatedResponse, MessageResponse

from app.admin.services import AdminService, UserService
from app.core.dependencies import PaginationParams, get_current_user_with_role
from app.core.limiter import limiter
from app.database.enums import UserRole
from app.database.models import User
from app.database.session import get_db

# ---------------------------------------------------
# Router Configuration
# ---------------------------------------------------
router = APIRouter(prefix="/admin", tags=["Admin"])
logger = logging.getLogger(__name__)

# ---------------------------------------------------
# Dependencies
# ---------------------------------------------------
DBDep = Annotated[AsyncSession, Depends(get_db)]
AuthenticatedAdminDep = Annotated[User, Depends(get_current_user_with_role(UserRole.ADMIN))]


# ---------------------------------------------------
# Helper Functions (Route level response building)
# ---------------------------------------------------
def build_status_response(user_id: UUID, action: str) -> UserStatusUpdateResponse:
    """Build a standard response for user status update actions."""
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
    response_model=PaginatedResponse[KYCPendingListItem],
    status_code=status.HTTP_200_OK,
    summary="List Pending KYC Submissions",
    description="Retrieve users with pending KYC submissions. Requires Admin role.",
)
@limiter.limit("10/minute")
async def get_pending_kyc_list(
    request: Request,
    db: DBDep,
    current_user: AuthenticatedAdminDep,
    pagination: PaginationParams = Depends(),
) -> PaginatedResponse[KYCPendingListItem]:
    """Retrieve a list of users with pending KYC submissions."""
    logger.info(f"[KYC] Admin {current_user.id} requested pending KYC list.")
    pending_kyc_items, total_count = await AdminService(db).list_pending_kyc(
        skip=pagination.skip, limit=pagination.limit
    )
    return PaginatedResponse(
        total_count=total_count,
        has_next_page=(pagination.skip + pagination.limit) < total_count,
        items=pending_kyc_items,
    )


@router.get(
    "/kyc/{user_id}",
    response_model=KYCDetailAdminView,
    status_code=status.HTTP_200_OK,
    summary="Get Specific KYC Details",
    description="Retrieve detailed information about a user's KYC submission. Requires Admin role.",
)
@limiter.limit("15/minute")
async def get_kyc_details(
    request: Request,
    user_id: UUID,
    db: DBDep,
    current_user: AuthenticatedAdminDep,
) -> KYCDetailAdminView:
    """Retrieve detailed KYC information for a specific user."""
    logger.info(f"[KYC] Admin {current_user.id} requesting KYC details for user {user_id}.")
    return await AdminService(db).get_kyc_detail(user_id)


@router.put(
    "/kyc/{user_id}/approve",
    response_model=KYCReviewActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve KYC Submission",
    description="Approve a specific user's KYC submission. Requires Admin role.",
)
@limiter.limit("5/minute")
async def approve_user_kyc(
    request: Request,
    user_id: UUID,
    db: DBDep,
    current_user: AuthenticatedAdminDep,
) -> KYCReviewActionResponse:
    """Approve a user's KYC submission."""
    logger.info(f"[KYC] Admin {current_user.id} approving KYC for user {user_id}.")
    return await AdminService(db).approve_kyc(user_id)


@router.put(
    "/kyc/{user_id}/reject",
    response_model=KYCReviewActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject KYC Submission",
    description="Reject a specific user's KYC submission. Requires Admin role.",
)
@limiter.limit("5/minute")
async def reject_user_kyc(
    request: Request,
    user_id: UUID,
    db: DBDep,
    current_user: AuthenticatedAdminDep,
) -> KYCReviewActionResponse:
    """Reject a user's KYC submission."""
    logger.info(f"[KYC] Admin {current_user.id} rejecting KYC for user {user_id}.")
    return await AdminService(db).reject_kyc(user_id)


@router.get(
    "/kyc/{user_id}/presigned-url/{doc_type}",
    response_model=PresignedUrlResponse | None,
    status_code=status.HTTP_200_OK,
    summary="Get Pre-signed URL for KYC Document",
    description="Generate a temporary secure URL to view a KYC document. Requires Admin role.",
)
@limiter.limit("20/minute")
async def get_kyc_document_presigned_url(
    request: Request,
    user_id: UUID,
    doc_type: Literal["document", "selfie"],
    db: DBDep,
    current_user: AuthenticatedAdminDep,
) -> PresignedUrlResponse | None:
    """Generate a secure pre-signed URL for accessing a user's KYC document."""
    logger.info(
        f"Admin {current_user.id} requesting presigned URL for user {user_id}, doc_type: {doc_type}."
    )
    admin_service = AdminService(db)
    generated_url_str = await admin_service.get_kyc_presigned_url(
        user_id=user_id, doc_type=doc_type
    )

    if not generated_url_str:
        logger.warning(f"[KYC] No document found for user {user_id} and doc_type {doc_type}.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No document found for the specified user and document type.",
        )

    try:
        validated_url = TypeAdapter(HttpUrl).validate_python(generated_url_str)
        return PresignedUrlResponse(url=validated_url)
    except ValidationError as e:
        logger.error(f"[KYC] URL validation failed for generated presigned URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to provide a valid access URL.")


# ---------------------------------------------------
# User Management Endpoints (Admin Only)
# ---------------------------------------------------
@router.get(
    "/users",
    response_model=list[AdminUserView],
    status_code=status.HTTP_200_OK,
    summary="List All Users",
    description="Retrieve a list of users with optional filters and pagination. Requires Admin role.",
)
@limiter.limit("10/minute")
async def list_all_users(
    request: Request,
    db: DBDep,
    current_user: AuthenticatedAdminDep,
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    role: UserRole | None = Query(None, description="Filter by user role (ADMIN, CLIENT, WORKER)"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    is_banned: bool | None = Query(None, description="Filter by banned status"),
    is_deleted: bool | None = Query(None, description="Include deleted users if true"),
) -> list[AdminUserView]:
    """Retrieve a paginated and optionally filtered list of users."""
    service = UserService(db)
    return await service.list_users(
        skip=skip,
        limit=limit,
        role=role,
        is_active=is_active,
        is_banned=is_banned,
        is_deleted=is_deleted,
    )


@router.get(
    "/users/{user_id}",
    response_model=AdminUserView,
    status_code=status.HTTP_200_OK,
    summary="Get User Details by ID",
    description="Retrieve detailed information for a specific user by their UUID. Requires Admin role.",
)
@limiter.limit("20/minute")
async def get_user_details(
    request: Request,
    user_id: UUID,
    db: DBDep,
    current_user: AuthenticatedAdminDep,
) -> AdminUserView:
    """Retrieve detailed information for a specific user."""
    service = UserService(db)
    return await service.get_user(user_id=user_id)


@router.put(
    "/users/{user_id}/freeze",
    response_model=UserStatusUpdateResponse,
    summary="Freeze User Account",
    description="Temporarily freeze a user's account. Requires Admin role.",
)
@limiter.limit("5/minute")
async def freeze_user_account(
    request: Request,
    user_id: UUID,
    db: DBDep,
    current_user: AuthenticatedAdminDep,
) -> UserStatusUpdateResponse:
    """Freeze a specific user's account."""
    logger.info(f"[USER] Admin {current_user.id} freezing user {user_id}.")
    await AdminService(db).freeze_user(user_id)
    return build_status_response(user_id, "frozen")


@router.put(
    "/users/{user_id}/unfreeze",
    response_model=UserStatusUpdateResponse,
    summary="Unfreeze User Account",
    description="Unfreeze a user's account. Requires Admin role.",
)
@limiter.limit("5/minute")
async def unfreeze_user_account(
    request: Request,
    user_id: UUID,
    db: DBDep,
    current_user: AuthenticatedAdminDep,
) -> UserStatusUpdateResponse:
    """Unfreeze a specific user's account."""
    logger.info(f"[USER] Admin {current_user.id} unfreezing user {user_id}.")
    await AdminService(db).unfreeze_user(user_id)
    return build_status_response(user_id, "unfrozen")


@router.put(
    "/users/{user_id}/ban",
    response_model=UserStatusUpdateResponse,
    summary="Ban User Account",
    description="Ban a user from the platform. Requires Admin role.",
)
@limiter.limit("5/minute")
async def ban_user_account(
    request: Request,
    user_id: UUID,
    db: DBDep,
    current_user: AuthenticatedAdminDep,
) -> UserStatusUpdateResponse:
    """Ban a specific user from the platform."""
    logger.info(f"[USER] Admin {current_user.id} banning user {user_id}.")
    await AdminService(db).ban_user(user_id)
    return build_status_response(user_id, "banned")


@router.put(
    "/users/{user_id}/unban",
    response_model=UserStatusUpdateResponse,
    summary="Unban User Account",
    description="Unban a previously banned user. Requires Admin role.",
)
@limiter.limit("5/minute")
async def unban_user_account(
    request: Request,
    user_id: UUID,
    db: DBDep,
    current_user: AuthenticatedAdminDep,
) -> UserStatusUpdateResponse:
    """Unban a specific user from the platform."""
    logger.info(f"[USER] Admin {current_user.id} unbanning user {user_id}.")
    await AdminService(db).unban_user(user_id)
    return build_status_response(user_id, "unbanned")


@router.delete(
    "/users/{user_id}",
    response_model=UserStatusUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="Soft Delete User Account",
    description="Soft delete a user's account (logical delete). Requires Admin role.",
)
@limiter.limit("3/minute")
async def delete_user_account(
    request: Request,
    user_id: UUID,
    db: DBDep,
    current_user: AuthenticatedAdminDep,
) -> UserStatusUpdateResponse:
    """Soft delete a specific user's account."""
    logger.info(f"[USER] Admin {current_user.id} soft deleting user {user_id}.")
    await AdminService(db).delete_user(user_id)
    return build_status_response(user_id, "deleted")


# ---------------------------------------------------
# Review Management Endpoints (Admin Only)
# ---------------------------------------------------
@router.get(
    "/reviews/flagged",
    response_model=PaginatedResponse[FlaggedReviewRead],
    status_code=status.HTTP_200_OK,
    summary="List Flagged Reviews",
    description="Retrieve a list of reviews flagged for moderation. Requires Admin role.",
)
@limiter.limit("10/minute")
async def get_flagged_reviews(
    request: Request,
    db: DBDep,
    current_user: AuthenticatedAdminDep,
    pagination: PaginationParams = Depends(),
) -> PaginatedResponse[FlaggedReviewRead]:
    """Retrieve a list of reviews flagged for moderation with pagination."""
    logger.info(f"[REVIEW] Admin {current_user.id} requested flagged reviews.")
    reviews, total_count = await AdminService(db).list_flagged_reviews(
        skip=pagination.skip, limit=pagination.limit
    )
    return PaginatedResponse(
        total_count=total_count,
        has_next_page=(pagination.skip + pagination.limit) < total_count,
        items=reviews,
    )


@router.delete(
    "/reviews/{review_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete Flagged Review",
    description="Delete a specific review that was flagged for moderation. Requires Admin role.",
)
@limiter.limit("5/minute")
async def delete_flagged_review(
    request: Request,
    review_id: UUID,
    db: DBDep,
    current_user: AuthenticatedAdminDep,
) -> MessageResponse:
    """Delete a flagged review from the platform."""
    logger.info(f"[REVIEW] Admin {current_user.id} deleting review {review_id}.")
    await AdminService(db).delete_review(review_id)
    return MessageResponse(detail="Review deleted.")


@router.get(
    "/profile/picture-url",
    response_model=PresignedUrlResponse | None,
    status_code=status.HTTP_200_OK,
    summary="Get Pre-signed URL for any user",
    description="Retrieve a temporary, secure URL to view the authenticated user's profile picture.",
)
@limiter.limit("30/minute")
async def get_user_profile_picture_url(
    request: Request,
    user_id: UUID,
    db: DBDep,
) -> PresignedUrlResponse | None:
    """Generate a presigned URL for the given user's profile picture."""
    logger.info(f"Requesting presigned URL for user {user_id}.")
    presigned_url_str = await UserService(db).get_public_profile_picture_presigned_url(
        user_id=user_id
    )

    if not presigned_url_str:
        return None

    try:
        validated_url = TypeAdapter(HttpUrl).validate_python(presigned_url_str)
        return PresignedUrlResponse(url=validated_url)
    except ValidationError as e:
        logger.error(f"Generated presigned URL failed validation for user {user_id}: {e}")
        return None
