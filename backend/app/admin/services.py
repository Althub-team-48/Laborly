"""
admin/services.py

Encapsulates business logic for administrative actions:
- KYC approvals and rejections
- User account management (ban, freeze, unfreeze, delete)
- Review moderation (listing and deleting flagged reviews)
"""

import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import KYC, User
from app.review.models import Review

logger = logging.getLogger(__name__)


class AdminService:
    """
    Service class containing methods for handling admin tasks.
    Includes KYC verification, user account control, and flagged review moderation.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------
    # KYC Verification
    # ------------------------------

    async def list_pending_kyc(self):
        """
        Retrieve all KYC records that are currently pending approval.
        """
        records = (await self.db.execute(select(KYC).filter(KYC.status == "PENDING"))).scalars().all()
        logger.info(f"[KYC] Fetched {len(records)} pending KYC submissions.")
        return records

    async def approve_kyc(self, user_id: UUID) -> KYC:
        """
        Approve a user's KYC submission.
        """
        kyc = (await self.db.execute(select(KYC).filter(KYC.user_id == user_id))).scalar_one_or_none()
        if not kyc:
            logger.warning(f"[KYC] KYC not found for user_id={user_id}")
            raise HTTPException(status_code=404, detail="KYC not found")

        kyc.status = "APPROVED"
        await self.db.commit()
        logger.info(f"[KYC] Approved for user_id={user_id}")
        return kyc

    async def reject_kyc(self, user_id: UUID) -> KYC:
        """
        Reject a user's KYC submission.
        """
        kyc = (await self.db.execute(select(KYC).filter(KYC.user_id == user_id))).scalar_one_or_none()
        if not kyc:
            logger.warning(f"[KYC] KYC not found for user_id={user_id}")
            raise HTTPException(status_code=404, detail="KYC not found")

        kyc.status = "REJECTED"
        await self.db.commit()
        logger.info(f"[KYC] Rejected for user_id={user_id}")
        return kyc

    # ------------------------------
    # User Account Control
    # ------------------------------

    async def freeze_user(self, user_id: UUID) -> User:
        """
        Temporarily deactivate a user's account (freeze).
        """
        user = await self._get_user_or_404(user_id)
        user.is_active = False
        await self.db.commit()
        logger.info(f"[USER] Frozen: user_id={user_id}")
        return user

    async def unfreeze_user(self, user_id: UUID) -> User:
        """
        Reactivate a frozen user's account.
        """
        user = await self._get_user_or_404(user_id)
        user.is_active = True
        await self.db.commit()
        logger.info(f"[USER] Unfrozen: user_id={user_id}")
        return user

    async def ban_user(self, user_id: UUID) -> User:
        """
        Ban a user from the platform.
        """
        user = await self._get_user_or_404(user_id)
        user.is_active = False
        await self.db.commit()
        logger.warning(f"[USER] Banned: user_id={user_id}")
        return user

    async def unban_user(self, user_id: UUID) -> User:
        """
        Unban a previously banned user.
        """
        user = await self._get_user_or_404(user_id)
        user.is_active = True
        await self.db.commit()
        logger.info(f"[USER] Unbanned: user_id={user_id}")
        return user

    async def delete_user(self, user_id: UUID) -> None:
        """
        Permanently delete a user's account.
        """
        user = await self._get_user_or_404(user_id)
        self.db.delete(user)
        await self.db.commit()
        logger.warning(f"[USER] Deleted: user_id={user_id}")

    # ------------------------------
    # Flagged Review Moderation
    # ------------------------------

    async def list_flagged_reviews(self):
        """
        Retrieve all reviews that have been flagged for moderation.
        """
        reviews = (await self.db.execute(select(Review).filter(Review.is_flagged.is_(True)))).scalars().all()
        logger.info(f"[REVIEW] Fetched {len(reviews)} flagged reviews.")
        return reviews

    async def delete_review(self, review_id: UUID) -> None:
        """
        Permanently delete a flagged review.
        """
        review = (await self.db.execute(select(Review).filter(Review.id == review_id))).scalar_one_or_none()
        if not review:
            logger.warning(f"[REVIEW] Not found: review_id={review_id}")
            raise HTTPException(status_code=404, detail="Review not found")

        self.db.delete(review)
        await self.db.commit()
        logger.warning(f"[REVIEW] Deleted: review_id={review_id}")

    # ------------------------------
    # Utility Methods
    # ------------------------------

    async def _get_user_or_404(self, user_id: UUID) -> User:
        """
        Helper method to retrieve a user or raise 404 if not found.
        """
        user = (await self.db.execute(select(User).filter(User.id == user_id))).scalar_one_or_none()
        if not user:
            logger.warning(f"[USER] Not found: user_id={user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        return user
