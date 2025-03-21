"""
[worker] service.py

Business logic for managing worker availability:
- Create, read, update, delete availability slots
- Ensure proper ownership validation
- Log significant actions for auditing
"""

from typing import List
from sqlalchemy.orm import Session

from database.models import WorkerAvailability
from workers.schemas import (
    WorkerAvailabilityCreate,
    WorkerAvailabilityUpdate,
    WorkerAvailabilityOut
)
from utils.logger import logger


class WorkerAvailabilityService:

    @staticmethod
    def create_availability(db: Session, availability: WorkerAvailabilityCreate, worker_id: int) -> WorkerAvailabilityOut:
        """
        Creates a new availability record for a worker.
        """
        try:
            db_availability = WorkerAvailability(
                worker_id=worker_id,
                start_time=availability.start_time,
                end_time=availability.end_time
            )
            db.add(db_availability)
            db.commit()
            db.refresh(db_availability)
            logger.info(f"Availability created: {db_availability.id} for worker {worker_id}")
            return WorkerAvailabilityOut.model_validate(db_availability)
        except Exception as e:
            logger.error(f"Error creating availability for worker {worker_id}: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def get_availability_by_id(db: Session, availability_id: int) -> WorkerAvailabilityOut:
        """
        Retrieves a specific availability slot by ID.
        """
        availability = db.query(WorkerAvailability).filter(WorkerAvailability.id == availability_id).first()
        if not availability:
            raise ValueError(f"Availability with ID {availability_id} not found")
        return WorkerAvailabilityOut.model_validate(availability)

    @staticmethod
    def get_worker_availability(db: Session, worker_id: int) -> List[WorkerAvailabilityOut]:
        """
        Fetches all availability slots belonging to the specified worker.
        """
        availabilities = db.query(WorkerAvailability).filter(WorkerAvailability.worker_id == worker_id).all()
        return [WorkerAvailabilityOut.model_validate(avail) for avail in availabilities]

    @staticmethod
    def update_availability(db: Session, availability_id: int, availability_update: WorkerAvailabilityUpdate, worker_id: int) -> WorkerAvailabilityOut:
        """
        Updates an availability slot.
        Only the worker who owns the slot may update it.
        """
        availability = db.query(WorkerAvailability).filter(WorkerAvailability.id == availability_id).first()
        if not availability:
            raise ValueError(f"Availability with ID {availability_id} not found")
        if availability.worker_id != worker_id:
            raise ValueError("You can only update your own availability")

        update_data = availability_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(availability, key, value)

        db.commit()
        db.refresh(availability)
        logger.info(f"Availability updated: {availability_id} for worker {worker_id}")
        return WorkerAvailabilityOut.model_validate(availability)

    @staticmethod
    def delete_availability(db: Session, availability_id: int, worker_id: int):
        """
        Deletes an availability slot.
        Only the worker who owns the slot may delete it.
        """
        availability = db.query(WorkerAvailability).filter(WorkerAvailability.id == availability_id).first()
        if not availability:
            raise ValueError(f"Availability with ID {availability_id} not found")
        if availability.worker_id != worker_id:
            raise ValueError("You can only delete your own availability")

        db.delete(availability)
        db.commit()
        logger.info(f"Availability deleted: {availability_id} for worker {worker_id}")
