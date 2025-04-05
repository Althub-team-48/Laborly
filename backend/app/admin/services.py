"""
admin/services.py

Encapsulates business logic for administrative actions:
- KYC approvals and rejections
- User management (ban, freeze, delete)
- Review moderation
"""

import logging
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.database.models import User, KYC
from app.review.models import Review

logger = logging.getLogger(__name__)


class AdminService:
    """
    Service layer for handling admin-specific tasks.
    """

    def __init__(self, db: Session):
        self.db = db

    # ----------------------------
    # KYC Management
    # ----------------------------

    def list_pending_kyc(self):
        """
        Fetch all KYC submissions with status 'PENDING'.
        """
        records = self.db.query(KYC).filter(KYC.status == "PENDING").all()
        logger.info(f"Fetched {len(records)} pending KYC submissions.")
        return records

    def approve_kyc(self, user_id: UUID) -> KYC:
        """
        Approve a user's KYC request.
        """
        kyc = self.db.query(KYC).filter_by(user_id=user_id).first()
        if not kyc:
            logger.warning(f"KYC not found for user_id={user_id}")
            raise HTTPException(status_code=404, detail="KYC not found")

        kyc.status = "APPROVED"
        self.db.commit()
        logger.info(f"KYC approved for user_id={user_id}")
        return kyc

    def reject_kyc(self, user_id: UUID) -> KYC:
        """
        Reject a user's KYC request.
        """
        kyc = self.db.query(KYC).filter_by(user_id=user_id).first()
        if not kyc:
            logger.warning(f"KYC not found for user_id={user_id}")
            raise HTTPException(status_code=404, detail="KYC not found")

        kyc.status = "REJECTED"
        self.db.commit()
        logger.info(f"KYC rejected for user_id={user_id}")
        return kyc

    # ----------------------------
    # User Status Management
    # ----------------------------

    def freeze_user(self, user_id: UUID) -> User:
        """
        Freeze a user (soft deactivate).
        """
        user = self._get_user_or_404(user_id)
        user.is_active = False
        self.db.commit()
        logger.info(f"User frozen: user_id={user_id}")
        return user

    def unfreeze_user(self, user_id: UUID) -> User:
        """
        Unfreeze (reactivate) a previously frozen user.
        """
        user = self._get_user_or_404(user_id)
        user.is_active = True
        self.db.commit()
        logger.info(f"User unfrozen: user_id={user_id}")
        return user

    def ban_user(self, user_id: UUID) -> User:
        """
        Ban a user from the platform.
        """
        user = self._get_user_or_404(user_id)
        user.is_active = False
        self.db.commit()
        logger.info(f"User banned: user_id={user_id}")
        return user

    def unban_user(self, user_id: UUID) -> User:
        """
        Unban a previously banned user.
        """
        user = self._get_user_or_404(user_id)
        user.is_active = True
        self.db.commit()
        logger.info(f"User unbanned: user_id={user_id}")
        return user

    def delete_user(self, user_id: UUID) -> None:
        """
        Permanently delete a user.
        """
        user = self._get_user_or_404(user_id)
        self.db.delete(user)
        self.db.commit()
        logger.info(f"User deleted: user_id={user_id}")

    # ----------------------------
    # Review Moderation
    # ----------------------------

    def list_flagged_reviews(self):
        """
        Return all reviews flagged for moderation.
        """
        reviews = self.db.query(Review).filter(Review.is_flagged.is_(True)).all()
        logger.info(f"Fetched {len(reviews)} flagged reviews.")
        return reviews

    def delete_review(self, review_id: UUID) -> None:
        """
        Permanently delete a review.
        """
        review = self.db.query(Review).filter_by(id=review_id).first()
        if not review:
            logger.warning(f"Review not found: review_id={review_id}")
            raise HTTPException(status_code=404, detail="Review not found")

        self.db.delete(review)
        self.db.commit()
        logger.info(f"Review deleted: review_id={review_id}")

    # ----------------------------
    # Internal Utility
    # ----------------------------

    def _get_user_or_404(self, user_id: UUID) -> User:
        """
        Retrieve a user or raise 404.
        """
        user = self.db.query(User).filter_by(id=user_id).first()
        if not user:
            logger.warning(f"User not found: user_id={user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        return user
