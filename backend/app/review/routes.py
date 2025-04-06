"""
routes.py

Defines API endpoints for job reviews:
- Submit a review
- Fetch reviews for a worker
- Fetch reviews by a client
- Get summary of a worker's reviews
"""

from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.review import schemas
from app.review.services import ReviewService
from core.dependencies import get_db, get_current_user_with_role
from app.database.models import User, UserRole

router = APIRouter(prefix="/reviews", tags=["Reviews"])


# ----------------------------------------
# Submit a review for a completed job
# ----------------------------------------
@router.post("/{job_id}", response_model=schemas.ReviewRead, status_code=status.HTTP_201_CREATED)
def submit_review(
    job_id: UUID,
    payload: schemas.ReviewWrite,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.CLIENT))
):
    """
    Submit a review for a completed job (Client only).
    """
    return ReviewService(db).submit_review(job_id=job_id, reviewer_id=current_user.id, data=payload)


# ----------------------------------------
# Get all reviews for a specific worker
# ----------------------------------------
@router.get("/worker/{worker_id}", response_model=list[schemas.ReviewRead])
def get_worker_reviews(
    worker_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Retrieve all reviews submitted for a worker (Public).
    """
    return ReviewService(db).get_reviews_for_worker(worker_id=worker_id)


# ----------------------------------------
# Get all reviews submitted by the client
# ----------------------------------------
@router.get("/my", response_model=list[schemas.ReviewRead])
def get_my_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.CLIENT))
):
    """
    Retrieve all reviews submitted by the authenticated client.
    """
    return ReviewService(db).get_reviews_by_client(client_id=current_user.id)


# ----------------------------------------
# Get review summary for a worker
# ----------------------------------------
@router.get("/summary/{worker_id}", response_model=schemas.WorkerReviewSummary)
def get_worker_review_summary(
    worker_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Returns average rating and total reviews for a given worker.
    """
    return ReviewService(db).get_review_summary(worker_id=worker_id)
