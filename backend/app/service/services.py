# backend/app/service/services.py

import logging
from uuid import UUID
from collections.abc import Sequence

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.service import models, schemas

logger = logging.getLogger(__name__)


class ServiceListingService:
    """
    Service layer for managing service listings.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_service(
        self, worker_id: UUID, data: schemas.ServiceCreate
    ) -> schemas.ServiceRead:
        logger.info(f"Creating new service for worker_id={worker_id}")
        service = models.Service(worker_id=worker_id, **data.model_dump())
        self.db.add(service)
        await self.db.commit()
        await self.db.refresh(service)
        logger.info(f"Service created: id={service.id}")
        return schemas.ServiceRead.model_validate(service, from_attributes=True)

    async def update_service(
        self, worker_id: UUID, service_id: UUID, data: schemas.ServiceUpdate
    ) -> schemas.ServiceRead:
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
        logger.info(f"Service updated: id={service.id}")
        return schemas.ServiceRead.model_validate(service, from_attributes=True)

    async def delete_service(self, worker_id: UUID, service_id: UUID) -> None:
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

    async def get_my_services(self, worker_id: UUID) -> list[models.Service]:
        """
        Return all services listed by the authenticated worker.
        Applies .unique() as Service model has joined loads.
        """
        logger.info(f"Fetching all services for worker_id={worker_id}")
        result = await self.db.execute(select(models.Service).filter_by(worker_id=worker_id))
        return list(result.unique().scalars().all())

    async def search_services(
        self, title: str | None = None, location: str | None = None
    ) -> list[models.Service]:
        """
        Public search for services by title and/or location.
        Applies .unique() to handle potential duplicates from joined loads.
        """
        logger.info(f"Searching services with title='{title}', location='{location}'")
        query = select(models.Service)

        if title:
            query = query.filter(models.Service.title.ilike(f"%{title}%"))

        if location:
            query = query.filter(models.Service.location.ilike(f"%{location}%"))

        result = await self.db.execute(query)

        services: Sequence[models.Service] = result.unique().scalars().all()

        logger.info(f"{len(services)} service(s) found matching criteria.")
        return list(services)
