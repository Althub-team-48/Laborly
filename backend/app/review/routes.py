"""
review/routes.py

Defines API endpoints related to job reviews:
- Submit a new review for a completed job
- Fetch all reviews received by a worker
- Fetch all reviews submitted by the current client
- Get a summary (average rating and count) for a specific worker
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.orm import Session

from app.review import schemas
from app.review.services import ReviewService
from app.core.dependencies import get_db, get_current_user_with_role
from app.database.models import User, UserRole
from app.core.limiter import limiter

router = APIRouter(prefix="/reviews", tags=["Reviews"])


# --------------------------------------------------------
# Submit Review (Client Only)
# --------------------------------------------------------
@router.post("/{job_id}", response_model=schemas.ReviewRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def submit_review(
    request: Request, 
    job_id: UUID,
    payload: schemas.ReviewWrite,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.CLIENT))
):
    """
    Submit a review for a completed job (Client only).
    """
    return ReviewService(db).submit_review(
        job_id=job_id,
        reviewer_id=current_user.id,
        data=payload
    )


# --------------------------------------------------------
# Get Reviews for a Worker (Public)
# --------------------------------------------------------
@router.get("/worker/{worker_id}", response_model=list[schemas.ReviewRead])
@limiter.limit("5/minute")
def get_worker_reviews(
    request: Request, 
    worker_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Retrieve all public reviews submitted for a worker.
    """
    return ReviewService(db).get_reviews_for_worker(worker_id=worker_id)


# --------------------------------------------------------
# Get Reviews by Client (Client Only)
# --------------------------------------------------------
@router.get("/my", response_model=list[schemas.ReviewRead])
@limiter.limit("5/minute")
def get_my_reviews(
    request: Request, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(UserRole.CLIENT))
):
    """
    Retrieve all reviews submitted by the current authenticated client.
    """
    return ReviewService(db).get_reviews_by_client(client_id=current_user.id)


# --------------------------------------------------------
# Get Review Summary for a Worker
# --------------------------------------------------------
@router.get("/summary/{worker_id}", response_model=schemas.WorkerReviewSummary)
@limiter.limit("5/minute")
def get_worker_review_summary(
    request: Request, 
    worker_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Returns average rating and total number of reviews for a specific worker.
    """
    return ReviewService(db).get_review_summary(worker_id=worker_id)
