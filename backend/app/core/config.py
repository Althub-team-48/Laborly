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
    DEBUG: bool
    LOG_LEVEL: str

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
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int

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
    MAIL_SERVER: str
    MAIL_PORT: int
    MAIL_STARTTLS: bool
    MAIL_SSL_TLS: bool
    MAIL_USE_CREDENTIALS: bool
    MAIL_VALIDATE_CERTS: bool
    MAIL_TEMPLATE_FOLDER: str
    SUPPORT_EMAIL: str

    # Frontend/Backend URLs
    BASE_URL: str

    # Bruteforce Protection
    MAX_FAILED_ATTEMPTS: int
    IP_PENALTY_DURATION: int
    FAILED_ATTEMPTS_WINDOW: int

    # Token Expiration
    EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES: int
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int
    NEW_EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES: int

    # OAuth State Token
    OAUTH_STATE_TOKEN_EXPIRE_MINUTES: int

    # CORS
    CORS_ALLOWED_ORIGINS: str

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]

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
        APP_NAME="dummy",
        DEBUG=False,
        DATABASE_URL="dummy",
        TEST_DATABASE_URL="dummy",
        SECRET_KEY="dummy",
        ALGORITHM="dummy",
        ACCESS_TOKEN_EXPIRE_MINUTES=0,
        GOOGLE_CLIENT_ID="dummy",
        GOOGLE_CLIENT_SECRET="dummy",
        AWS_ACCESS_KEY_ID="dummy",
        AWS_SECRET_ACCESS_KEY="dummy",
        AWS_REGION="dummy",
        AWS_S3_BUCKET="dummy",
        MAIL_USERNAME="dummy",
        MAIL_PASSWORD="dummy",
        MAIL_FROM="dummy",
        MAIL_FROM_NAME="dummy",
        SUPPORT_EMAIL="dummy",
        LOG_LEVEL="dummy",
        REDIS_HOST="dummy",
        REDIS_PORT=0,
        REDIS_DB=0,
        MAIL_SERVER="dummy",
        MAIL_PORT=0,
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        MAIL_USE_CREDENTIALS=True,
        MAIL_VALIDATE_CERTS=True,
        MAIL_TEMPLATE_FOLDER="dummy",
        BASE_URL="dummy",
        EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES=0,
        PASSWORD_RESET_TOKEN_EXPIRE_MINUTES=0,
        NEW_EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES=0,
        MAX_FAILED_ATTEMPTS=0,
        IP_PENALTY_DURATION=0,
        FAILED_ATTEMPTS_WINDOW=0,
        CORS_ALLOWED_ORIGINS="dummy",
        OAUTH_STATE_TOKEN_EXPIRE_MINUTES=0,
    )
else:
    settings = Settings()
