"""
[reviews] service.py

Provides review-related business logic:
- Creation, filtering, updating, deletion
- Recalculates average rating on review changes
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from database.models import Review, Job, JobStatus, User
from reviews.schemas import ReviewCreate, ReviewUpdate, ReviewOut
from utils.logger import logger, log_system_action
from core.exceptions import APIError


class ReviewService:
    @staticmethod
    def create_review(db: Session, review: ReviewCreate, reviewer_id: int) -> ReviewOut:
        """
        Creates a new review for a completed job.
        Validates permissions, prevents duplicates, and updates average rating.
        """
        job = db.query(Job).filter(Job.id == review.job_id).first()
        if not job or job.status != JobStatus.COMPLETED:
            raise ValueError("Reviews can only be submitted for completed jobs")

        # Determine valid reviewee
        if reviewer_id == job.client_id:
            reviewee_id = job.worker_id
        elif reviewer_id == job.worker_id:
            reviewee_id = job.client_id
        else:
            raise ValueError("You must be the client or worker of this job to review")

        if reviewee_id != review.reviewee_id:
            raise ValueError("Invalid reviewee for this job")

        # Prevent duplicate review
        if db.query(Review).filter_by(job_id=review.job_id, reviewer_id=reviewer_id).first():
            raise ValueError("You have already reviewed this job")

        # Create review
        db_review = Review(
            job_id=review.job_id,
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id,
            rating=review.rating
        )
        db.add(db_review)
        db.commit()
        db.refresh(db_review)

        # Update rating
        ReviewService.update_average_rating(db, reviewee_id)

        log_system_action(db, reviewer_id, "CREATE", f"Review {db_review.id} created for user {reviewee_id}")
        logger.info(f"Review created: {db_review.id} by {reviewer_id} for {reviewee_id}")
        return ReviewOut.model_validate(db_review)

    @staticmethod
    def update_average_rating(db: Session, user_id: int) -> None:
        """
        Recalculates and updates the average rating for a user.
        """
        avg_rating = db.query(func.avg(Review.rating)).filter(Review.reviewee_id == user_id).scalar()
        if avg_rating is not None:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.average_rating = round(avg_rating, 1)
                db.commit()
                logger.info(f"Updated average rating for user {user_id} to {user.average_rating}")
        else:
            logger.warning(f"No reviews found for user {user_id}, average rating unchanged")

    @staticmethod
    def get_reviews_by_job(db: Session, job_id: int) -> List[ReviewOut]:
        """
        Retrieves all reviews for a given job.
        """
        reviews = db.query(Review).filter(Review.job_id == job_id).all()
        return [ReviewOut.model_validate(review) for review in reviews]

    @staticmethod
    def get_reviews_by_user(
        db: Session,
        user_id: int,
        rating: Optional[int] = None,
        role: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[ReviewOut]:
        """
        Retrieves reviews where the user is the reviewee.
        Optional filters include rating, reviewer role, and date range.
        """
        query = db.query(Review).filter(Review.reviewee_id == user_id)

        if rating:
            query = query.filter(Review.rating == rating)
        if role:
            reviewer_role = role.upper()
            if reviewer_role not in ["CLIENT", "WORKER"]:
                raise ValueError("Role must be 'CLIENT' or 'WORKER'")
            query = query.join(User, Review.reviewer_id == User.id).filter(User.role == reviewer_role)
        if date_from:
            query = query.filter(Review.created_at >= date_from)
        if date_to:
            query = query.filter(Review.created_at <= date_to)

        reviews = query.all()
        return [ReviewOut.model_validate(review) for review in reviews]

    @staticmethod
    def update_review(db: Session, review_id: int, review_update: ReviewUpdate) -> ReviewOut:
        """
        Updates a review record (admin only).
        Also triggers average rating recalculation for the reviewee.
        """
        review = db.query(Review).filter(Review.id == review_id).first()
        if not review:
            raise ValueError("Review not found")

        update_data = review_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(review, key, value)

        db.commit()
        db.refresh(review)
        ReviewService.update_average_rating(db, review.reviewee_id)

        log_system_action(db, None, "UPDATE", f"Review {review_id} updated by admin")
        logger.info(f"Review updated: {review_id}")
        return ReviewOut.model_validate(review)

    @staticmethod
    def delete_review(db: Session, review_id: int) -> None:
        """
        Deletes a review record (admin only) and updates reviewee rating.
        """
        review = db.query(Review).filter(Review.id == review_id).first()
        if not review:
            raise ValueError("Review not found")

        reviewee_id = review.reviewee_id
        db.delete(review)
        db.commit()

        ReviewService.update_average_rating(db, reviewee_id)

        log_system_action(db, None, "DELETE", f"Review {review_id} deleted by admin")
        logger.info(f"Review deleted: {review_id}")
