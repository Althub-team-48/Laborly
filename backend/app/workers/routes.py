"""
[workers] routes.py

Defines endpoints for worker availability:
- Create, read, update, delete availability slots
- Access restricted to workers, with admin override for viewing
"""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from workers.schemas import (
    WorkerAvailabilityCreate,
    WorkerAvailabilityUpdate,
    WorkerAvailabilityOut,
    WorkerAvailabilityList,
)
from workers.service import WorkerAvailabilityService
from core.dependencies import get_db, get_current_user
from core.exceptions import APIError
from users.schemas import UserOut, UserRole

router = APIRouter(
    prefix="/api/workers/availability",
    tags=["Worker Availability"]
)


@router.post("/", response_model=WorkerAvailabilityOut, status_code=status.HTTP_201_CREATED, responses={
    201: {"description": "Availability slot created"},
    403: {"description": "Permission denied"},
    500: {"description": "Failed to create availability slot"}
})
def create_availability(
    availability: WorkerAvailabilityCreate,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """
    Create a new availability slot for a worker.
    Only workers are authorized to create their availability.
    """
    if current_user.role != UserRole.WORKER:
        raise APIError(status_code=403, message="Only workers can set availability")

    try:
        return WorkerAvailabilityService.create_availability(db, availability, current_user.id)
    except Exception as e:
        raise APIError(status_code=500, message=str(e))


@router.get("/me", response_model=WorkerAvailabilityList, responses={
    200: {"description": "List of availability slots"},
    403: {"description": "Only workers can view their availability"}
})
def list_my_availability(
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """
    Retrieve all availability slots for the authenticated worker.
    """
    if current_user.role != UserRole.WORKER:
        raise APIError(status_code=403, message="Only workers can view their availability")

    return {
        "availabilities": WorkerAvailabilityService.get_worker_availability(db, current_user.id)
    }


@router.get("/{availability_id}", response_model=WorkerAvailabilityOut, responses={
    200: {"description": "Availability slot retrieved"},
    403: {"description": "Access denied"},
    404: {"description": "Availability not found"},
    500: {"description": "Failed to retrieve availability"}
})
def get_availability(
    availability_id: int,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """
    Retrieve a specific availability slot by ID.
    Admins can view any slot. Workers can only view their own slots.
    """
    try:
        availability = WorkerAvailabilityService.get_availability_by_id(db, availability_id)
        if current_user.role != UserRole.ADMIN and availability.worker.id != current_user.id:
            raise ValueError("You can only view your own availability")
        return availability
    except ValueError as e:
        raise APIError(status_code=403, message=str(e))
    except Exception as e:
        raise APIError(status_code=500, message=str(e))


@router.put("/{availability_id}", response_model=WorkerAvailabilityOut, responses={
    200: {"description": "Availability updated successfully"},
    403: {"description": "Permission denied"},
    404: {"description": "Availability not found"},
    500: {"description": "Failed to update availability"}
})
def update_availability(
    availability_id: int,
    availability_update: WorkerAvailabilityUpdate,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """
    Update an existing availability slot.
    Only the owning worker may perform this action.
    """
    if current_user.role != UserRole.WORKER:
        raise APIError(status_code=403, message="Only workers can update their availability")

    try:
        return WorkerAvailabilityService.update_availability(
            db, availability_id, availability_update, current_user.id
        )
    except ValueError as e:
        raise APIError(status_code=403, message=str(e))
    except Exception as e:
        raise APIError(status_code=500, message=str(e))


@router.delete("/{availability_id}", status_code=status.HTTP_204_NO_CONTENT, responses={
    204: {"description": "Availability deleted"},
    403: {"description": "Permission denied"},
    404: {"description": "Availability not found"},
    500: {"description": "Failed to delete availability"}
})
def delete_availability(
    availability_id: int,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """
    Delete an availability slot.
    Only the owning worker may perform this action.
    """
    if current_user.role != UserRole.WORKER:
        raise APIError(status_code=403, message="Only workers can delete their availability")

    try:
        WorkerAvailabilityService.delete_availability(db, availability_id, current_user.id)
    except ValueError as e:
        raise APIError(status_code=403, message=str(e))
    except Exception as e:
        raise APIError(status_code=500, message=str(e))
