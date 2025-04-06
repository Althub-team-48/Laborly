"""
services.py

Business logic for handling job reviews:
- Submit a review
- Retrieve reviews for a worker or by a client
- Compute review summary for a worker
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
    def __init__(self, db: Session):
        self.db = db

    # ----------------------------------------
    # Submit Review (Client can review a job only once)
    # ----------------------------------------
    def submit_review(self, job_id: UUID, reviewer_id: UUID, data: schemas.ReviewWrite) -> models.Review:
        logger.info(f"Client {reviewer_id} submitting review for job {job_id}")

        # Ensure job exists and belongs to the reviewer (client)
        job = self.db.query(Job).filter_by(id=job_id, client_id=reviewer_id).first()
        if not job:
            logger.warning("Unauthorized or non-existent job for review submission")
            raise HTTPException(status_code=403, detail="Unauthorized or job not found")

        # Ensure review is not already submitted
        if self.db.query(models.Review).filter_by(job_id=job_id).first():
            logger.warning("Duplicate review detected for job")
            raise HTTPException(status_code=400, detail="Review already submitted for this job")

        # Create and persist review
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

        logger.info(f"Review submitted successfully: review_id={review.id}")
        return review

    # ----------------------------------------
    # Get All Reviews for a Worker (Public)
    # ----------------------------------------
    def get_reviews_for_worker(self, worker_id: UUID):
        logger.info(f"Retrieving reviews for worker {worker_id}")
        return self.db.query(models.Review).filter_by(worker_id=worker_id).all()

    # ----------------------------------------
    # Get All Reviews by a Client (Private)
    # ----------------------------------------
    def get_reviews_by_client(self, client_id: UUID):
        logger.info(f"Retrieving reviews submitted by client {client_id}")
        return self.db.query(models.Review).filter_by(reviewer_id=client_id).all()

    # ----------------------------------------
    # Get Summary of Reviews for a Worker
    # ----------------------------------------
    def get_review_summary(self, worker_id: UUID) -> schemas.WorkerReviewSummary:
        logger.info(f"Calculating review summary for worker {worker_id}")
        avg_rating, total_reviews = self.db.query(
            func.coalesce(func.avg(models.Review.rating), 0),
            func.count(models.Review.id)
        ).filter_by(worker_id=worker_id).first()

        summary = schemas.WorkerReviewSummary(
            average_rating=round(avg_rating, 2),
            total_reviews=total_reviews
        )
        logger.debug(f"Review summary calculated: {summary}")
        return summary
