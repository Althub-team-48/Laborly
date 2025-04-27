"""
backend/app/review/services.py

Review Services
Business logic for handling job reviews:
- Submit a new review (one per job) (Authenticated Client)
- Retrieve reviews for a specific worker or by a client (Public/Authenticated)
- Compute average rating and review count summary for a worker (Public)
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.job.models import Job
from app.review import models, schemas

logger = logging.getLogger(__name__)


# ---------------------------------------------------
# Review Service
# ---------------------------------------------------
class ReviewService:
    """Service layer for managing job reviews."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the service with a database session."""
        self.db = db

    # ---------------------------------------------------
    # Review Submission
    # ---------------------------------------------------
    async def submit_review(
        self, job_id: UUID, reviewer_id: UUID, data: schemas.ReviewWrite
    ) -> models.Review:
        """
        Submit a review for a completed job.
        Ensures the job belongs to the reviewer and has not already been reviewed.
        """
        logger.info(f"[SUBMIT] Client {reviewer_id} submitting review for job {job_id}")

        result = await self.db.execute(select(Job).filter_by(id=job_id, client_id=reviewer_id))
        job = result.scalars().first()

        if not job:
            logger.warning(f"[SUBMIT] Unauthorized or job not found: job_id={job_id}")
            raise HTTPException(status_code=403, detail="Unauthorized or job not found")

        result = await self.db.execute(select(models.Review).filter_by(job_id=job_id))
        if result.scalars().first():
            logger.warning(f"[SUBMIT] Duplicate review attempt: job_id={job_id}")
            raise HTTPException(status_code=400, detail="Review already submitted for this job")

        review = models.Review(
            client_id=reviewer_id,
            worker_id=job.worker_id,
            job_id=job_id,
            rating=data.rating,
            review_text=data.text,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)

        logger.info(f"[SUBMIT] Review created successfully: review_id={review.id}")
        return review

    # ---------------------------------------------------
    # Review Retrieval
    # ---------------------------------------------------
    async def get_reviews_for_worker(
        self, worker_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[models.Review], int]:
        """
        Fetch all reviews received by a specific worker with pagination and total count.
        (Used for public and authenticated views)
        """
        logger.info(f"[LIST] Retrieving reviews for worker_id={worker_id}")

        # Count total records
        count_stmt = select(func.count()).filter(models.Review.worker_id == worker_id)
        total_count_result = await self.db.execute(count_stmt)
        total_count = total_count_result.scalar_one()

        # Fetch paginated records
        result = await self.db.execute(
            select(models.Review).filter_by(worker_id=worker_id).offset(skip).limit(limit)
        )
        reviews = list(result.scalars().all())

        return reviews, total_count

    async def get_reviews_by_client(
        self, client_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[models.Review], int]:
        """
        Fetch all reviews submitted by a specific client with pagination and total count.
        (Authenticated client action)
        """
        logger.info(f"[LIST] Retrieving reviews by client_id={client_id}")

        # Count total records
        count_stmt = select(func.count()).filter(models.Review.client_id == client_id)
        total_count_result = await self.db.execute(count_stmt)
        total_count = total_count_result.scalar_one()

        # Fetch paginated records
        result = await self.db.execute(
            select(models.Review).filter_by(client_id=client_id).offset(skip).limit(limit)
        )
        reviews = list(result.scalars().all())

        return reviews, total_count

    # ---------------------------------------------------
    # Review Summary Calculation
    # ---------------------------------------------------

    async def get_review_summary(self, worker_id: UUID) -> schemas.WorkerReviewSummary:
        """
        Calculate average rating and total review count for a worker.
        (Publicly accessible)
        """
        logger.info(f"[SUMMARY] Calculating review summary for worker_id={worker_id}")
        result = await self.db.execute(
            select(
                func.coalesce(func.avg(models.Review.rating), 0),
                func.count(models.Review.id),
            ).filter(models.Review.worker_id == worker_id)
        )

        avg_rating, total_reviews = result.first()
        summary = schemas.WorkerReviewSummary(
            average_rating=round(float(avg_rating), 2) if avg_rating else 0.0,
            total_reviews=total_reviews if total_reviews is not None else 0,
        )

        logger.debug(f"[SUMMARY] Computed summary: {summary}")
        return summary
