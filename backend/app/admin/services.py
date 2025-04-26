"""
backend/app/admin/services.py

Admin and User Services

Encapsulates business logic for administrative operations, including:
- KYC submissions approval and rejection
- User account control (freeze, unfreeze, ban, unban, delete)
- Flagged review moderation (listing and deletion)
- User listing and user detail retrieval

All administrative operations are restricted to authenticated Admin users.
"""

import logging
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.upload import generate_presigned_url, get_s3_key_from_url
from app.database.enums import KYCStatus, UserRole
from app.database.models import KYC, User
from app.review.models import Review
from app.worker.models import WorkerProfile

logger = logging.getLogger(__name__)


# ---------------------------------------------------
# Admin and User Services
# ---------------------------------------------------
class AdminService:
    """
    Service class for handling administrative operations.
    Includes KYC verification, user account control, and flagged review moderation.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize AdminService with a database session.
        """
        self.db = db

    # ---------------------------------------------------
    # Internal Helper Methods
    # ---------------------------------------------------
    async def _get_kyc_or_404(self, user_id: UUID) -> KYC:
        """
        Internal helper to fetch a KYC record or raise 404.
        """
        stmt = select(KYC).filter(KYC.user_id == user_id)
        result = await self.db.execute(stmt)
        kyc_record = result.scalar_one_or_none()

        if not kyc_record:
            logger.error(f"[KYC] Record not found for user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="KYC record not found.",
            )
        return kyc_record

    async def _get_user_or_404(self, user_id: UUID) -> User:
        """
        Internal helper to fetch a User record or raise 404.
        """
        stmt = select(User).filter(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            logger.error(f"[USER] Record not found for user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )
        return user

    # ---------------------------------------------------
    # KYC Verification (Admin Only)
    # ---------------------------------------------------

    async def list_pending_kyc(self) -> list[KYC]:
        """
        Retrieve all KYC records that are currently pending approval.
        """
        result = await self.db.execute(
            select(KYC).filter(KYC.status == KYCStatus.PENDING).order_by(KYC.submitted_at.asc())
        )
        records = list(result.scalars())
        logger.info(f"[KYC] Fetched {len(records)} pending KYC submissions.")
        return records

    async def get_kyc_details_for_admin(self, user_id: UUID) -> KYC:
        """
        Retrieve detailed KYC information for a specific user.
        """
        logger.info(f"[KYC] Fetching details for user_id={user_id}")
        stmt = select(KYC).filter(KYC.user_id == user_id)
        result = await self.db.execute(stmt)
        kyc_record = result.unique().scalar_one_or_none()

        if not kyc_record:
            logger.warning(f"[KYC] Details not found for user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="KYC record not found for this user.",
            )

        logger.info(f"[KYC] Details retrieved for user_id={user_id}, status={kyc_record.status}")
        return kyc_record

    async def approve_kyc(self, user_id: UUID) -> KYC:
        """
        Approve a user's KYC submission and update the reviewed timestamp.
        """
        kyc = await self._get_kyc_or_404(user_id)

        if kyc.status == KYCStatus.APPROVED:
            logger.warning(
                f"[KYC] Attempt to re-approve already approved KYC for user_id={user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="KYC is already approved.",
            )

        worker_profile_result = await self.db.execute(
            select(WorkerProfile).filter(WorkerProfile.user_id == user_id)
        )
        worker_profile = worker_profile_result.unique().scalar_one_or_none()

        if worker_profile:
            worker_profile.is_kyc_verified = True
            logger.info(
                f"[KYC Approve] Set WorkerProfile.is_kyc_verified=True for user_id={user_id}"
            )
            await self.db.refresh(worker_profile)
        else:
            logger.warning(
                f"[KYC Approve] WorkerProfile not found for user_id={user_id}. Skipping is_kyc_verified update."
            )

        kyc.status = KYCStatus.APPROVED
        kyc.reviewed_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(kyc)

        logger.info(f"[KYC] Approved for user_id={user_id}")
        return kyc

    async def reject_kyc(self, user_id: UUID) -> KYC:
        """
        Reject a user's KYC submission and update the reviewed timestamp.
        """
        kyc = await self._get_kyc_or_404(user_id)

        if kyc.status == KYCStatus.REJECTED:
            logger.warning(f"[KYC] Attempt to re-reject already rejected KYC for user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="KYC is already rejected.",
            )

        worker_profile_result = await self.db.execute(
            select(WorkerProfile).filter(WorkerProfile.user_id == user_id)
        )
        worker_profile = worker_profile_result.unique().scalar_one_or_none()

        if worker_profile:
            worker_profile.is_kyc_verified = False
            logger.info(
                f"[KYC Reject] Set WorkerProfile.is_kyc_verified=False for user_id={user_id}"
            )
            await self.db.refresh(worker_profile)
        else:
            logger.warning(
                f"[KYC Reject] WorkerProfile not found for user_id={user_id}. Skipping is_kyc_verified update."
            )

        kyc.status = KYCStatus.REJECTED
        kyc.reviewed_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(kyc)

        logger.info(f"[KYC] Rejected for user_id={user_id}")
        return kyc

    async def get_kyc_presigned_url(
        self, user_id: UUID, doc_type: Literal["document", "selfie"]
    ) -> str:
        """
        Generate a pre-signed URL for a user's KYC document.
        """
        logger.info(f"[KYC] Requesting pre-signed URL for user_id={user_id}, doc_type='{doc_type}'")
        kyc_record = await self._get_kyc_or_404(user_id)

        s3_full_url = None
        if doc_type == "document":
            s3_full_url = kyc_record.document_path
        elif doc_type == "selfie":
            s3_full_url = kyc_record.selfie_path

        if not s3_full_url:
            logger.warning(f"[KYC] S3 path missing for doc_type='{doc_type}' user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"S3 path for '{doc_type}' not found in KYC record.",
            )

        s3_key = get_s3_key_from_url(s3_full_url)
        if not s3_key:
            logger.error(f"[KYC] Failed to extract S3 key from URL: {s3_full_url}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not process stored S3 document path.",
            )

        presigned_url = generate_presigned_url(s3_key)
        if not presigned_url:
            logger.error(f"[KYC] Failed to generate pre-signed URL for S3 key: {s3_key}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not generate secure access URL for the document.",
            )

        return presigned_url

    # ---------------------------------------------------
    # User Account Control (Admin Only)
    # ---------------------------------------------------

    async def freeze_user(self, user_id: UUID) -> User:
        """
        Temporarily deactivate a user's account (freeze).
        """
        user = await self._get_user_or_404(user_id)
        if user.is_frozen:
            logger.warning(f"[USER Freeze] Attempt to freeze already frozen user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is already frozen.",
            )

        user.is_frozen = True
        user.is_active = False
        await self.db.commit()
        await self.db.refresh(user)
        logger.info(f"[USER] Frozen: user_id={user_id}")
        return user

    async def unfreeze_user(self, user_id: UUID) -> User:
        """
        Reactivate a frozen user's account.
        """
        user = await self._get_user_or_404(user_id)
        if not user.is_frozen:
            logger.warning(
                f"[USER Unfreeze] Attempt to unfreeze user_id={user_id} who is not frozen."
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is not currently frozen.",
            )

        user.is_frozen = False
        if not user.is_banned:
            user.is_active = True
        await self.db.commit()
        await self.db.refresh(user)
        logger.info(f"[USER] Unfrozen: user_id={user_id}")
        return user

    async def ban_user(self, user_id: UUID) -> User:
        """
        Ban a user from the platform.
        """
        user = await self._get_user_or_404(user_id)
        if user.is_banned:
            logger.warning(f"[USER Ban] Attempt to ban already banned user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is already banned.",
            )

        user.is_banned = True
        user.is_active = False
        user.is_frozen = False
        await self.db.commit()
        await self.db.refresh(user)
        logger.warning(f"[USER] Banned: user_id={user_id}")
        return user

    async def unban_user(self, user_id: UUID) -> User:
        """
        Unban a previously banned user.
        """
        user = await self._get_user_or_404(user_id)
        if not user.is_banned:
            logger.warning(f"[USER Unban] Attempt to unban user_id={user_id} who is not banned.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is not currently banned.",
            )

        user.is_banned = False
        if not user.is_frozen:
            user.is_active = True
        await self.db.commit()
        await self.db.refresh(user)
        logger.info(f"[USER] Unbanned: user_id={user_id}")
        return user

    async def delete_user(self, user_id: UUID) -> None:
        """
        Soft delete a user account.
        """
        user = await self._get_user_or_404(user_id)
        if user.is_deleted:
            logger.warning(f"[USER Delete] Attempt to delete already deleted user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is already marked as deleted.",
            )

        user.is_deleted = True
        user.is_active = False
        user.is_frozen = False
        user.is_banned = False
        await self.db.commit()
        logger.warning(f"[USER] Soft Deleted: user_id={user_id}")

    # ---------------------------------------------------
    # Flagged Review Moderation (Admin Only)
    # ---------------------------------------------------

    async def list_flagged_reviews(self) -> list[Review]:
        """
        Retrieve all reviews flagged for moderation.
        """
        result = await self.db.execute(select(Review).filter(Review.is_flagged.is_(True)))
        reviews = list(result.scalars())
        logger.info(f"[REVIEW] Fetched {len(reviews)} flagged reviews.")
        return reviews

    async def delete_review(self, review_id: UUID) -> None:
        """
        Delete a specific flagged review.
        """
        review = (
            (await self.db.execute(select(Review).filter(Review.id == review_id)))
            .unique()
            .scalar_one_or_none()
        )
        if not review:
            logger.warning(f"[REVIEW] Not found: review_id={review_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found.",
            )

        await self.db.delete(review)
        await self.db.commit()
        logger.warning(f"[REVIEW] Deleted: review_id={review_id}")


class UserService:
    """
    Service class for listing and retrieving users with optional filters.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all_users(
        self,
        skip: int = 0,
        limit: int = 100,
        role: UserRole | None = None,
        is_active: bool | None = None,
        is_banned: bool | None = None,
        is_deleted: bool | None = None,
    ) -> list[User]:
        """
        Retrieve users with optional filtering by role, status, and deletion flag.
        """
        stmt = select(User)
        if role is not None:
            stmt = stmt.filter(User.role == role)
        if is_active is not None:
            stmt = stmt.filter(User.is_active == is_active)
        if is_banned is not None:
            stmt = stmt.filter(User.is_banned == is_banned)
        if is_deleted is not None:
            stmt = stmt.filter(User.is_deleted == is_deleted)
        else:
            stmt = stmt.filter(User.is_deleted.is_(False))

        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_user_details(self, user_id: UUID) -> User:
        """
        Retrieve detailed information for a specific user.
        """
        stmt = select(User).filter(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )
        return user
