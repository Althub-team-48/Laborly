"""
env.py

This is the Alembic environment script used to configure the migration context.
It handles both offline and online migrations for the SQLAlchemy ORM models.

Key Features:
- Loads environment variables from `.env`
- Dynamically sets the database URL for Alembic
- Sets up logging
- Uses SQLAlchemy metadata for autogenerate support
"""

import sys
import os

# Extend the Python path to allow importing modules from parent directories
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
print(f"Loaded DATABASE_URL: {os.getenv('DATABASE_URL')}")

# Alembic configuration object
config = context.config

# Set the sqlalchemy.url from environment variable
database_url = os.getenv("DATABASE_URL")
if database_url is None:
    raise ValueError("DATABASE_URL environment variable is not set")

config.set_main_option("sqlalchemy.url", database_url)

# Set up Python logging using the Alembic config
fileConfig(config.config_file_name)

# Import SQLAlchemy metadata for 'autogenerate' support
from database.config import Base
from database.models import *  # Ensure models are registered

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    This configures the context with just a URL and not an Engine.
    """
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    This uses an Engine and connects to the database for migration execution.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# Determine whether to run migrations online or offline
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
