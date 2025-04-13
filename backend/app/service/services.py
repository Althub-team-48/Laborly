"""
service/services.py

Handles business logic for worker service listings:
- Create, update, delete services
- Search service listings
"""

import logging
from uuid import UUID
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.service import models, schemas

logger = logging.getLogger(__name__)


class ServiceListingService:
    """
    Service layer for managing service listings.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_service(self, worker_id: UUID, data: schemas.ServiceCreate) -> models.Service:
        """
        Create a new service entry for a worker.
        """
        logger.info(f"Creating new service for worker_id={worker_id}")
        service = models.Service(worker_id=worker_id, **data.model_dump())
        self.db.add(service)
        await self.db.commit()
        await self.db.refresh(service)
        logger.info(f"Service created: id={service.id}")
        return service

    async def update_service(self, worker_id: UUID, service_id: UUID, data: schemas.ServiceUpdate) -> models.Service:
        """
        Update an existing service belonging to the worker.
        """
        logger.info(f"Updating service_id={service_id} for worker_id={worker_id}")
        result = await self.db.execute(
            select(models.Service).filter_by(id=service_id, worker_id=worker_id)
        )
        service = result.scalars().first()

        if not service:
            logger.warning(f"Service not found or unauthorized: service_id={service_id}")
            raise HTTPException(status_code=404, detail="Service not found or unauthorized")

        # Apply only provided fields
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(service, field, value)

        await self.db.commit()
        await self.db.refresh(service)
        logger.info(f"Service updated: id={service.id}")
        return service

    async def delete_service(self, worker_id: UUID, service_id: UUID) -> None:
        """
        Delete a service if owned by the worker.
        """
        logger.info(f"Deleting service_id={service_id} for worker_id={worker_id}")
        result = await self.db.execute(
            select(models.Service).filter_by(id=service_id, worker_id=worker_id)
        )
        service = result.scalars().first()

        if not service:
            logger.warning(f"Service not found or unauthorized: service_id={service_id}")
            raise HTTPException(status_code=404, detail="Service not found or unauthorized")

        self.db.delete(service)
        await self.db.commit()
        logger.info(f"Service deleted successfully: id={service_id}")

    async def get_my_services(self, worker_id: UUID) -> List[models.Service]:
        """
        Return all services listed by the authenticated worker.
        """
        logger.info(f"Fetching all services for worker_id={worker_id}")
        result = await self.db.execute(
            select(models.Service).filter_by(worker_id=worker_id)
        )
        return result.scalars().all()

    async def search_services(self, title: Optional[str] = None, location: Optional[str] = None) -> List[models.Service]:
        """
        Public search for services by title and/or location.
        """
        logger.info("Searching services...")
        query = select(models.Service)

        if title:
            query = query.filter(models.Service.title.ilike(f"%{title}%"))

        if location:
            query = query.filter(models.Service.location.ilike(f"%{location}%"))

        result = await self.db.execute(query)
        services = result.scalars().all()
        logger.info(f"{len(services)} service(s) found")
        return services
