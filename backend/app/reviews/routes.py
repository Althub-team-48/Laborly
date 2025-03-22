"""
[reviews] routes.py

Defines API endpoints for managing job-related reviews:
- Create, retrieve, update, and delete reviews
- Role-based access control for clients, workers, and admins
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from utils.logger import logger
from reviews.schemas import ReviewCreate, ReviewUpdate, ReviewOut, ReviewList
from reviews.service import ReviewService
from core.dependencies import get_db, get_current_user, get_admin_user
from core.exceptions import APIError
from users.schemas import UserOut
from users.schemas import UserRole

router = APIRouter(prefix="/api/reviews", tags=["Reviews"])


@router.post("/", response_model=ReviewOut, status_code=status.HTTP_201_CREATED, responses={
    201: {"description": "Review created"},
    400: {"description": "Invalid input"},
    403: {"description": "Access denied"},
    500: {"description": "Server error"},
})
def create_review(
    review: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """
    Submit a review for a completed job.
    Accessible by authenticated users.
    """
    try:
        return ReviewService.create_review(db, review, current_user.id)
    except ValueError as e:
        raise APIError(status_code=400, message=str(e))
    except Exception as e:
        logger.error(f"Error creating review: {str(e)}")
        raise APIError(status_code=500, message="Internal server error")


@router.get("/job/{job_id}", response_model=ReviewList, responses={
    200: {"description": "List of reviews for the job"},
    403: {"description": "Access denied"},
    404: {"description": "Job not found"},
})
def get_reviews_by_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """
    Retrieve all reviews for a specific job.
    Accessible by the job's client, assigned worker, or admin.
    """
    from jobs.service import JobService  # Avoid circular import

    job = JobService.get_job_by_id(db, job_id)

    if current_user.role != UserRole.ADMIN and job.client.id != current_user.id and job.worker_id != current_user.id:
        raise APIError(status_code=403, message="You can only view reviews for your own jobs")

    return {"reviews": ReviewService.get_reviews_by_job(db, job_id)}


@router.get("/user/{user_id}", response_model=ReviewList, responses={
    200: {"description": "List of reviews for the user"},
    403: {"description": "Access denied"},
    500: {"description": "Server error"},
})
def get_reviews_by_user(
    user_id: int,
    rating: Optional[int] = None,
    role: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """
    Retrieve reviews written about a specific user.
    Admins can view any; users can view their own.
    Supports filters: rating, role, date range.
    """
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise APIError(status_code=403, message="You can only view your own reviews")

    try:
        reviews = ReviewService.get_reviews_by_user(db, user_id, rating, role, date_from, date_to)
        return {"reviews": reviews}
    except ValueError as e:
        raise APIError(status_code=400, message=str(e))
    except Exception as e:
        logger.error(f"Error fetching user reviews: {str(e)}")
        raise APIError(status_code=500, message="Internal server error")


@router.put("/{review_id}", response_model=ReviewOut, dependencies=[Depends(get_admin_user)], responses={
    200: {"description": "Review fully updated"},
    400: {"description": "Invalid data"},
    404: {"description": "Review not found"},
    500: {"description": "Server error"},
})
def update_review(
    review_id: int,
    review_update: ReviewUpdate,
    db: Session = Depends(get_db)
):
    """
    Fully update a review.
    Admin-only access.
    """
    try:
        return ReviewService.update_review(db, review_id, review_update)
    except ValueError as e:
        raise APIError(status_code=404, message=str(e))
    except Exception as e:
        logger.error(f"Error updating review {review_id}: {str(e)}")
        raise APIError(status_code=500, message="Internal server error")


# @router.patch("/{review_id}", response_model=ReviewOut, dependencies=[Depends(get_admin_user)], responses={
#     200: {"description": "Review partially updated"},
#     400: {"description": "Invalid data"},
#     404: {"description": "Review not found"},
#     500: {"description": "Server error"},
# })
# def partial_update_review(
#     review_id: int,
#     review_update: ReviewUpdate,
#     db: Session = Depends(get_db)
# ):
#     """
#     Partially update a review.
#     Admin-only access.
#     """
#     try:
#         return ReviewService.update_review(db, review_id, review_update)
#     except ValueError as e:
#         raise APIError(status_code=404, message=str(e))
#     except Exception as e:
#         logger.error(f"Error patching review {review_id}: {str(e)}")
#         raise APIError(status_code=500, message="Internal server error")


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_admin_user)], responses={
    204: {"description": "Review deleted"},
    404: {"description": "Review not found"},
    500: {"description": "Server error"},
})
def delete_review(
    review_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a review by ID.
    Admin-only access.
    """
    try:
        ReviewService.delete_review(db, review_id)
    except ValueError as e:
        raise APIError(status_code=404, message=str(e))
    except Exception as e:
        logger.error(f"Error deleting review {review_id}: {str(e)}")
        raise APIError(status_code=500, message="Internal server error")
