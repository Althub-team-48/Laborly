"""
service/services.py

Handles business logic for worker service listings:
- Create, update, delete services
- Search service listings
"""

import logging
from uuid import UUID
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.service import models, schemas

logger = logging.getLogger(__name__)


class ServiceListingService:
    """
    Encapsulates all service-related operations for workers.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_service(self, worker_id: UUID, data: schemas.ServiceCreate) -> models.Service:
        """
        Create a new service listing for a worker.
        """
        logger.info(f"Creating new service for worker_id={worker_id}")
        service = models.Service(worker_id=worker_id, **data.model_dump())
        self.db.add(service)
        self.db.commit()
        self.db.refresh(service)
        logger.info(f"Service created: id={service.id}")
        return service

    def update_service(self, worker_id: UUID, service_id: UUID, data: schemas.ServiceUpdate) -> models.Service:
        """
        Update an existing service listing owned by a worker.
        """
        logger.info(f"Updating service_id={service_id} for worker_id={worker_id}")
        service = self.db.query(models.Service).filter_by(id=service_id, worker_id=worker_id).first()

        if not service:
            logger.warning("Service not found or unauthorized")
            raise HTTPException(status_code=404, detail="Service not found or unauthorized")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(service, field, value)

        self.db.commit()
        self.db.refresh(service)
        logger.info(f"Service updated: id={service.id}")
        return service

    def delete_service(self, worker_id: UUID, service_id: UUID) -> None:
        """
        Delete a service owned by a worker.
        """
        logger.info(f"Deleting service_id={service_id} for worker_id={worker_id}")
        service = self.db.query(models.Service).filter_by(id=service_id, worker_id=worker_id).first()

        if not service:
            logger.warning("Service not found or unauthorized")
            raise HTTPException(status_code=404, detail="Service not found or unauthorized")

        self.db.delete(service)
        self.db.commit()
        logger.info("Service deleted successfully")

    def get_my_services(self, worker_id: UUID) -> List[models.Service]:
        """
        Retrieve all services owned by a worker.
        """
        logger.info(f"Fetching all services for worker_id={worker_id}")
        return self.db.query(models.Service).filter_by(worker_id=worker_id).all()

    def search_services(self, title: Optional[str] = None, location: Optional[str] = None) -> List[models.Service]:
        """
        Search for services by optional title and location filters.
        """
        logger.info("Searching services")
        query = self.db.query(models.Service)

        if title:
            query = query.filter(models.Service.title.ilike(f"%{title}%"))
        if location:
            query = query.filter(models.Service.location.ilike(f"%{location}%"))

        results = query.all()
        logger.info(f"{len(results)} service(s) found")
        return results
