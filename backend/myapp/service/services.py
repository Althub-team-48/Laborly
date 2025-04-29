"""
backend/app/service/services.py

Service Listing Service
Handles business logic for managing service listings including:
- Creating, updating, and deleting services
- Fetching services (personal and public)
- Public search functionality
"""

import logging
from collections.abc import Sequence
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from myapp.service import models, schemas

logger = logging.getLogger(__name__)


# ---------------------------------------------------
# Service Listing Service
# ---------------------------------------------------


class ServiceListingService:
    """Service layer for managing service listings."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the service with a database session."""
        self.db = db

    # ---------------------------------------------------
    # Service Management Methods
    # ---------------------------------------------------

    async def create_service(self, worker_id: UUID, data: schemas.ServiceCreate) -> models.Service:
        """Create a new service listing for a worker."""
        logger.info(f"Creating new service for worker_id={worker_id}")
        service = models.Service(worker_id=worker_id, **data.model_dump())
        self.db.add(service)
        await self.db.commit()
        await self.db.refresh(service)
        logger.info(f"Service created successfully: id={service.id}")
        return service

    async def update_service(
        self, worker_id: UUID, service_id: UUID, data: schemas.ServiceUpdate
    ) -> models.Service:
        """Update an existing service listing (must belong to worker or admin)."""
        logger.info(f"Updating service_id={service_id} for worker_id={worker_id}")
        result = await self.db.execute(
            select(models.Service).filter_by(id=service_id, worker_id=worker_id)
        )
        service = result.scalars().first()

        if not service:
            logger.warning(f"Service not found or unauthorized: service_id={service_id}")
            raise HTTPException(status_code=404, detail="Service not found or unauthorized")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(service, field, value)

        await self.db.commit()
        await self.db.refresh(service)
        logger.info(f"Service updated successfully: id={service.id}")
        return service

    async def delete_service(self, worker_id: UUID, service_id: UUID) -> None:
        """Delete an existing service listing (must belong to worker or admin)."""
        logger.info(f"Deleting service_id={service_id} for worker_id={worker_id}")
        result = await self.db.execute(
            select(models.Service).filter_by(id=service_id, worker_id=worker_id)
        )
        service = result.scalars().first()

        if not service:
            logger.warning(f"Service not found or unauthorized: service_id={service_id}")
            raise HTTPException(status_code=404, detail="Service not found or unauthorized")

        await self.db.delete(service)
        await self.db.commit()
        logger.info(f"Service deleted successfully: id={service_id}")

    async def get_my_services(
        self, worker_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[models.Service], int]:
        """Retrieve all services listed by the authenticated worker with pagination and total count."""
        logger.info(f"Fetching all services for worker_id={worker_id}")

        # Count total records
        count_stmt = select(func.count()).filter(models.Service.worker_id == worker_id)
        total_count_result = await self.db.execute(count_stmt)
        total_count = total_count_result.scalar_one()

        # Fetch paginated records
        result = await self.db.execute(
            select(models.Service).filter_by(worker_id=worker_id).offset(skip).limit(limit)
        )
        return list(result.unique().scalars().all()), total_count

    async def get_public_service_detail(self, service_id: UUID) -> models.Service:
        """Retrieve public detailed information for a specific service."""
        logger.info(f"Fetching public service detail for service_id={service_id}")
        result = await self.db.execute(select(models.Service).filter_by(id=service_id))
        service = result.scalars().first()

        if not service:
            logger.warning(f"Service not found: service_id={service_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

        return service

    async def search_services(
        self, title: str | None = None, location: str | None = None, skip: int = 0, limit: int = 100
    ) -> tuple[list[models.Service], int]:
        """Search services publicly by title and/or location with pagination and total count."""
        logger.info(f"Searching services with title='{title}', location='{location}'")
        query = select(models.Service)

        if title:
            query = query.filter(models.Service.title.ilike(f"%{title}%"))

        if location:
            query = query.filter(models.Service.location.ilike(f"%{location}%"))

        # Count total records for the filtered query
        count_stmt = select(func.count()).select_from(query.subquery())
        total_count_result = await self.db.execute(count_stmt)
        total_count = total_count_result.scalar_one()

        # Fetch paginated records
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        services: Sequence[models.Service] = result.unique().scalars().all()

        logger.info(
            f"{len(services)} service(s) found matching search criteria (Total: {total_count})."
        )
        return list(services), total_count
