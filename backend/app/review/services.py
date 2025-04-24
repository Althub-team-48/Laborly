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

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.review import schemas, models
from app.job.models import Job

logger = logging.getLogger(__name__)


class ReviewService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def submit_review(
        self, job_id: UUID, reviewer_id: UUID, data: schemas.ReviewWrite
    ) -> models.Review:
        """
        Submit a review for a completed job.
        Ensures the job belongs to the reviewer and hasn't been reviewed already.
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
            reviewer_id=reviewer_id,
            worker_id=job.worker_id,
            job_id=job_id,
            rating=data.rating,
            text=data.text,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)
        logger.info(f"[SUBMIT] Review created successfully: review_id={review.id}")
        return review

    async def get_reviews_for_worker(self, worker_id: UUID) -> list[models.Review]:
        """
        Fetch all reviews received by a given worker.
        """
        logger.info(f"[LIST] Retrieving reviews for worker_id={worker_id}")
        result = await self.db.execute(select(models.Review).filter_by(worker_id=worker_id))
        return list(result.scalars().all())

    async def get_reviews_by_client(self, client_id: UUID) -> list[models.Review]:
        """
        Fetch all reviews submitted by a specific client.
        """
        logger.info(f"[LIST] Retrieving reviews by client_id={client_id}")
        result = await self.db.execute(select(models.Review).filter_by(reviewer_id=client_id))
        return list(result.scalars().all())

    async def get_review_summary(self, worker_id: UUID) -> schemas.WorkerReviewSummary:
        """
        Calculate average rating and total review count for a worker.
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
            total_reviews=total_reviews,
        )
        logger.debug(f"[SUMMARY] Computed summary: {summary}")
        return summary
