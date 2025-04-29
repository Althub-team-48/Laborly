"""
alembic/env.py

Alembic environment configuration for database migrations.
- Supports both offline and asynchronous online migration contexts.
- Loads SQLAlchemy engine and metadata from project base.
"""

from logging.config import fileConfig
from alembic import context
from sqlalchemy.ext.asyncio import AsyncEngine

# --- Load SQLAlchemy base metadata and engine ---
from myapp.database.session import engine as async_engine
from myapp.database.base import Base

# --- Import models to ensure they are registered with SQLAlchemy and visible to Alembic ---
from myapp.database import models
from myapp.client import models as client_models
from myapp.worker import models as worker_models
from myapp.job import models as job_models
from myapp.review import models as review_models
from myapp.service import models as service_models
from myapp.messaging import models as messaging_models


# --- Alembic config and logger ---
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode (no DB connection needed).
    """
    context.configure(
        url=str(async_engine.url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode using async engine.
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: context.configure(
                connection=sync_conn,
                target_metadata=target_metadata,
                compare_type=True,
                compare_server_default=True,
            )
        )
        await conn.run_sync(lambda sync_conn: context.run_migrations())


# --- Entry point ---
if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio

    asyncio.run(run_migrations_online())
