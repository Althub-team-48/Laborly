"""
review/services.py

Business logic for handling job reviews:
- Submit a new review (one per job)
- Retrieve reviews for a specific worker or by a client
- Compute average rating and count summary for a worker
"""

import logging
from uuid import UUID
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.review import schemas, models
from app.job.models import Job

logger = logging.getLogger(__name__)


class ReviewService:
    """
    Encapsulates review-related logic, including:
    - Validated submission
    - Listing for worker/client
    - Review statistics
    """

    def __init__(self, db: Session):
        self.db = db

    # ----------------------------------------------------
    # Submit Review (Only one per job allowed)
    # ----------------------------------------------------
    def submit_review(self, job_id: UUID, reviewer_id: UUID, data: schemas.ReviewWrite) -> models.Review:
        """
        Submit a new review for a completed job by the client.
        Ensures one review per job and valid job ownership.
        """
        logger.info(f"[SUBMIT] Client {reviewer_id} submitting review for job {job_id}")

        # Verify job belongs to the client
        job = self.db.query(Job).filter_by(id=job_id, client_id=reviewer_id).first()
        if not job:
            logger.warning(f"[SUBMIT] Job not found or unauthorized: job_id={job_id}")
            raise HTTPException(status_code=403, detail="Unauthorized or job not found")

        # Prevent duplicate review submission
        if self.db.query(models.Review).filter_by(job_id=job_id).first():
            logger.warning(f"[SUBMIT] Duplicate review attempt: job_id={job_id}")
            raise HTTPException(status_code=400, detail="Review already submitted for this job")

        # Create review record
        review = models.Review(
            reviewer_id=reviewer_id,
            worker_id=job.worker_id,
            job_id=job_id,
            rating=data.rating,
            text=data.text,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)

        logger.info(f"[SUBMIT] Review created successfully: review_id={review.id}")
        return review

    # ----------------------------------------------------
    # Get All Reviews for a Worker (Public)
    # ----------------------------------------------------
    def get_reviews_for_worker(self, worker_id: UUID):
        """
        Retrieve all reviews submitted for a given worker.
        """
        logger.info(f"[LIST] Retrieving reviews for worker_id={worker_id}")
        return self.db.query(models.Review).filter_by(worker_id=worker_id).all()

    # ----------------------------------------------------
    # Get All Reviews by a Client (Private)
    # ----------------------------------------------------
    def get_reviews_by_client(self, client_id: UUID):
        """
        Retrieve all reviews submitted by a specific client.
        """
        logger.info(f"[LIST] Retrieving reviews by client_id={client_id}")
        return self.db.query(models.Review).filter_by(reviewer_id=client_id).all()

    # ----------------------------------------------------
    # Get Review Summary for a Worker
    # ----------------------------------------------------
    def get_review_summary(self, worker_id: UUID) -> schemas.WorkerReviewSummary:
        """
        Return average rating and total review count for a worker.
        """
        logger.info(f"[SUMMARY] Calculating review summary for worker_id={worker_id}")

        avg_rating, total_reviews = self.db.query(
            func.coalesce(func.avg(models.Review.rating), 0),
            func.count(models.Review.id)
        ).filter_by(worker_id=worker_id).first()

        summary = schemas.WorkerReviewSummary(
            average_rating=round(avg_rating, 2),
            total_reviews=total_reviews
        )

        logger.debug(f"[SUMMARY] Calculated: {summary}")
        return summary
