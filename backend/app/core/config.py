"""
core/config.py

Loads and manages application configuration from environment variables.
Utilizes Pydantic BaseSettings for type validation and `.env` support.
"""

import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    """
    Application-wide settings loaded from environment variables.
    """
    APP_NAME: str
    DEBUG: bool = False
    DATABASE_URL: str
    TEST_DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    model_config = ConfigDict(
            env_file=".env",    # Load variables from .env file
            extra="forbid"      # controls undeclared vars, false by default
        )

    @property
    def db_url(self) -> str:
        """Dynamically resolves the appropriate database URL based on the current environment. If running tests (detected via PYTEST_CURRENT_TEST), use TEST_DATABASE_URL. Otherwise, use the main DATABASE_URL. Prevents accidental writes to production DB during testing."""
        is_testing = os.getenv("PYTEST_CURRENT_TEST") is not None
        url = self.TEST_DATABASE_URL if is_testing else self.DATABASE_URL
        if not url:
            raise RuntimeError("Database URL is not set for the current environment.")
        return url

# Instantiate the settings for global use
settings = Settings()
