"""
env.py

Alembic environment configuration for database migrations.
- Sets up offline and online migration contexts.
- Loads SQLAlchemy engine and metadata from project base.
"""

from logging.config import fileConfig
from sqlalchemy import pool
from alembic import context

# --- Load SQLAlchemy base metadata and engine ---
from app.database.session import engine
from app.database.base import Base
from app.database import models  # ensures models are loaded for Base.metadata
from app.client import models as client_models
from app.worker import models as worker_models
from app.job import models as job_models


# --- Alembic Config object ---
config = context.config

# --- Configure logging if config file is present ---
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Set metadata for automatic migration generation ---
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    This configures the context with just a URL and doesn't require a DB connection.
    """
    context.configure(
        url=str(engine.url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    This connects to the database and runs migrations with an active connection.
    """
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


# --- Entry point ---
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
