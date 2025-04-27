"""
backend/app/core/config.py

Application Configuration Loader

Loads and manages application settings from environment variables
using Pydantic's BaseSettings with `.env` support.
Provides strict type validation and environment-specific handling.
"""

import logging
import os
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------
# Logger Configuration
# ---------------------------------------------------
logger = logging.getLogger(__name__)

# Load environment variables from `.env` file
load_dotenv()


# ---------------------------------------------------
# Settings Definition
# ---------------------------------------------------
class Settings(BaseSettings):
    """
    Application-wide settings loaded from environment variables.
    """

    # General
    APP_NAME: str
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str
    TEST_DATABASE_URL: str

    # JWT Authentication
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # OAuth2 - Google
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # AWS S3 Storage
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str
    AWS_S3_BUCKET: str

    # Email Service
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_FROM_NAME: str
    MAIL_SERVER: str = "smtp.example.com"
    MAIL_PORT: int = 587
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    MAIL_USE_CREDENTIALS: bool = True
    MAIL_VALIDATE_CERTS: bool = True
    MAIL_TEMPLATE_FOLDER: str = "templates/email"
    SUPPORT_EMAIL: str

    # Frontend/Backend URLs
    FRONTEND_URL: str = "http://localhost:5000"
    BACKEND_URL: str = "http://localhost:8000"

    # Token Expiration
    EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    NEW_EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    @property
    def db_url(self) -> str:
        """
        Resolve the appropriate database URL based on environment.
        Uses the test database URL if running under pytest.
        """
        is_testing = os.getenv("PYTEST_CURRENT_TEST") is not None
        url = self.TEST_DATABASE_URL if is_testing else self.DATABASE_URL
        print("🔍 Using DATABASE URL:", url)  # Optional: remove for production
        logger.debug(f"[CONFIG] Using DATABASE URL: {url}")

        if not url:
            raise RuntimeError("Database URL is not set for the current environment.")

        return url

    model_config = SettingsConfigDict(env_file=".env", extra="forbid")


# ---------------------------------------------------
# Instantiate Settings Globally
# ---------------------------------------------------
if TYPE_CHECKING:
    # Stub settings for type hinting and editor assistance
    settings = Settings(
        APP_NAME="MyApp",
        DEBUG=False,
        DATABASE_URL="sqlite:///fake.db",
        TEST_DATABASE_URL="sqlite:///test.db",
        SECRET_KEY="secret",
        ALGORITHM="HS256",
        ACCESS_TOKEN_EXPIRE_MINUTES=30,
        GOOGLE_CLIENT_ID="dummy",
        GOOGLE_CLIENT_SECRET="dummy",
        AWS_ACCESS_KEY_ID="dummy",
        AWS_SECRET_ACCESS_KEY="dummy",
        AWS_REGION="us-east-1",
        AWS_S3_BUCKET="dummy-bucket",
        MAIL_USERNAME="email@example.com",
        MAIL_PASSWORD="pass",
        MAIL_FROM="email@example.com",
        MAIL_FROM_NAME="Laborly",
        SUPPORT_EMAIL="support@example.com",
    )
else:
    settings = Settings()
