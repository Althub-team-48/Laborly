"""
admin/services.py

Encapsulates business logic for administrative actions:
- KYC approvals and rejections
- User account management (ban, freeze, unfreeze, delete)
- Review moderation (listing and deleting flagged reviews)
"""

import logging
from typing import Literal
from uuid import UUID
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.enums import KYCStatus
from app.database.models import KYC, User
from app.review.models import Review
from app.core.upload import generate_presigned_url, get_s3_key_from_url
from app.worker.models import WorkerProfile

logger = logging.getLogger(__name__)


class AdminService:
    """
    Service class containing methods for handling admin tasks.
    Includes KYC verification, user account control, and flagged review moderation.
    """

    def __init__(self, db: AsyncSession):
        """
        Initializes the AdminService with a database session.
        """
        self.db = db

    # ---------------------------------------------------
    # KYC Verification
    # ---------------------------------------------------
    async def list_pending_kyc(self) -> list[KYC]:
        """
        Retrieve all KYC records that are currently pending approval.
        Returns the full KYC model objects.
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
        # eager load related user data if needed in the response schema later
        # stmt = select(KYC).options(selectinload(KYC.user)).filter(KYC.user_id == user_id)
        stmt = select(KYC).filter(KYC.user_id == user_id)
        result = await self.db.execute(stmt)
        kyc_record = result.unique().scalar_one_or_none()

        if not kyc_record:
            logger.warning(f"[KYC] Details not found for user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="KYC record not found for this user."
            )

        logger.info(f"[KYC] Details retrieved for user_id={user_id}, status={kyc_record.status}")
        return kyc_record

    async def approve_kyc(self, user_id: UUID) -> KYC:
        """
        Approve a user's KYC submission and update the reviewed timestamp.

        Returns:
            The updated KYC model object.

        Raises:
            HTTPException (404): If the KYC record for the given user ID is not found.
            HTTPException (400): If the KYC is already approved.
        """
        kyc = await self._get_kyc_or_404(user_id)

        if kyc.status == KYCStatus.APPROVED:
            logger.warning(
                f"[KYC] Attempt to re-approve already approved KYC for user_id={user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="KYC is already approved."
            )

        worker_profile_result = await self.db.execute(
            select(WorkerProfile).filter(WorkerProfile.user_id == user_id)
        )
        worker_profile = worker_profile_result.unique().scalar_one_or_none()

        if not worker_profile:
            logger.warning(
                f"[KYC Approve] WorkerProfile not found for user_id={user_id}. Cannot update is_kyc_verified flag on profile."
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Worker profile not found for this user.",
            )
        else:
            worker_profile.is_kyc_verified = True
            logger.info(
                f"[KYC Approve] Set WorkerProfile.is_kyc_verified=True for user_id={user_id}"
            )

        kyc.status = KYCStatus.APPROVED
        kyc.reviewed_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(kyc)
        if worker_profile:
            await self.db.refresh(worker_profile)

        logger.info(f"[KYC] Approved for user_id={user_id}")
        return kyc

    async def reject_kyc(self, user_id: UUID) -> KYC:
        """
        Reject a user's KYC submission and update the reviewed timestamp.

        Returns:
            The updated KYC model object.

        Raises:
            HTTPException (404): If the KYC record for the given user ID is not found.
            HTTPException (400): If the KYC is already rejected.
        """
        kyc = await self._get_kyc_or_404(user_id)

        if kyc.status == KYCStatus.REJECTED:
            logger.warning(f"[KYC] Attempt to re-reject already rejected KYC for user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="KYC is already rejected."
            )

        worker_profile_result = await self.db.execute(
            select(WorkerProfile).filter(WorkerProfile.user_id == user_id)
        )
        worker_profile = worker_profile_result.unique().scalar_one_or_none()

        if not worker_profile:
            logger.warning(
                f"[KYC Reject] WorkerProfile not found for user_id={user_id}. Cannot update is_kyc_verified flag on profile."
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Worker profile not found for this user.",
            )
        else:
            worker_profile.is_kyc_verified = False
            logger.info(
                f"[KYC Reject] Set WorkerProfile.is_kyc_verified=False for user_id={user_id}"
            )

        kyc.status = KYCStatus.REJECTED
        kyc.reviewed_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(kyc)
        if worker_profile:
            await self.db.refresh(worker_profile)

        logger.info(f"[KYC] Rejected for user_id={user_id}")
        return kyc

    async def get_kyc_presigned_url(
        self, user_id: UUID, doc_type: Literal["document", "selfie"]
    ) -> str:
        """
        Retrieves a KYC record and generates a pre-signed URL for a specific document.
        (Implementation from previous step)
        """
        logger.info(f"Requesting pre-signed URL for user_id={user_id}, doc_type='{doc_type}'")
        kyc_record = await self._get_kyc_or_404(user_id)

        s3_full_url = None
        if doc_type == "document":
            s3_full_url = kyc_record.document_path
        elif doc_type == "selfie":
            s3_full_url = kyc_record.selfie_path

        if not s3_full_url:
            logger.warning(f"S3 path for doc_type='{doc_type}' is missing for user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"S3 path for '{doc_type}' not found in KYC record.",
            )

        s3_key = get_s3_key_from_url(s3_full_url)
        if not s3_key:
            logger.error(f"Could not extract S3 key from stored URL: {s3_full_url}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not process stored S3 document path.",
            )

        presigned_url = generate_presigned_url(s3_key)
        if not presigned_url:
            logger.error(f"Failed to generate pre-signed URL for S3 key: {s3_key}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not generate secure access URL for the document.",
            )

        return presigned_url

    # ---------------------------------------------------
    # User Account Control
    # ---------------------------------------------------
    async def freeze_user(self, user_id: UUID) -> User:
        user = await self._get_user_or_404(user_id)
        user.is_frozen = True
        await self.db.commit()
        logger.info(f"[USER] Frozen: user_id={user_id}")
        return user

    async def unfreeze_user(self, user_id: UUID) -> User:
        user = await self._get_user_or_404(user_id)
        user.is_frozen = False
        await self.db.commit()
        logger.info(f"[USER] Unfrozen: user_id={user_id}")
        return user

    async def ban_user(self, user_id: UUID) -> User:
        user = await self._get_user_or_404(user_id)
        user.is_banned = True
        user.is_active = False
        await self.db.commit()
        logger.warning(f"[USER] Banned: user_id={user_id}")
        return user

    async def unban_user(self, user_id: UUID) -> User:
        user = await self._get_user_or_404(user_id)
        user.is_banned = False
        user.is_active = True
        await self.db.commit()
        logger.info(f"[USER] Unbanned: user_id={user_id}")
        return user

    async def delete_user(self, user_id: UUID) -> None:
        """
        Soft delete a user's account by marking is_deleted = True.
        """
        user = await self._get_user_or_404(user_id)
        user.is_deleted = True
        user.is_active = False
        # clear sensitive data like email/phone if required by policy
        # user.email = f"deleted_{user.id}@example.com"
        # user.phone_number = f"deleted_{user.id}"
        await self.db.commit()
        logger.warning(f"[USER] Soft Deleted: user_id={user_id}")

    # ---------------------------------------------------
    # Flagged Review Moderation
    # ---------------------------------------------------
    async def list_flagged_reviews(self) -> list[Review]:
        result = await self.db.execute(select(Review).filter(Review.is_flagged.is_(True)))
        reviews = list(result.scalars())
        logger.info(f"[REVIEW] Fetched {len(reviews)} flagged reviews.")
        return reviews

    async def delete_review(self, review_id: UUID) -> None:
        review = (
            (await self.db.execute(select(Review).filter(Review.id == review_id)))
            .unique()
            .scalar_one_or_none()
        )
        if not review:
            logger.warning(f"[REVIEW] Not found: review_id={review_id}")
            raise HTTPException(status_code=404, detail="Review not found")

        await self.db.delete(review)
        await self.db.commit()
        logger.warning(f"[REVIEW] Deleted: review_id={review_id}")

    # ---------------------------------------------------
    # Utility Methods
    # ---------------------------------------------------
    async def _get_user_or_404(self, user_id: UUID) -> User:
        """Helper method to retrieve a user or raise 404 if not found."""
        user = (
            (await self.db.execute(select(User).filter(User.id == user_id)))
            .unique()
            .scalar_one_or_none()
        )
        if not user:
            logger.warning(f"[UTIL] User not found: user_id={user_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    async def _get_kyc_or_404(self, user_id: UUID) -> KYC:
        """Helper method to retrieve a KYC record or raise 404 if not found."""
        kyc = (
            (await self.db.execute(select(KYC).filter(KYC.user_id == user_id)))
            .unique()
            .scalar_one_or_none()
        )
        if not kyc:
            logger.warning(f"[UTIL] KYC record not found for user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="KYC record not found for this user."
            )
        return kyc
