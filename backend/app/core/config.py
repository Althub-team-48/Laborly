"""
backend/app/core/config.py

Application Configuration Loader

Loads and manages application settings from environment variables
using Pydantic's BaseSettings with `.env` support.
Provides strict type validation and environment-specific handling.
"""

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------
# Logger Configuration
# ---------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------
# Base Directory Calculation
# ---------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DOTENV_PATH = BASE_DIR / ".env"


# ---------------------------------------------------
# Settings Definition
# ---------------------------------------------------
class Settings(BaseSettings):
    """
    Application-wide settings loaded from environment variables.
    """

    # --- Pydantic Settings Configuration ---
    model_config = SettingsConfigDict(
        env_file=str(DEFAULT_DOTENV_PATH),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- General Application Settings ---
    APP_NAME: str
    DEBUG: bool
    LOG_LEVEL: str
    BASE_URL: str

    # --- Database Settings ---
    DATABASE_URL: str
    TEST_DATABASE_URL: str

    # --- JWT Authentication Settings ---
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # --- OAuth2 - Google ---
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

    # --- Redis Settings ---
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int

    # --- AWS S3 Storage Settings ---
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str
    AWS_S3_BUCKET: str

    # --- Email Service Settings---
    SENDGRID_API_KEY: str
    MAIL_FROM: EmailStr
    MAIL_FROM_NAME: str
    EMAILS_ENABLED: bool
    MAIL_TEMPLATES_DIR: str
    SUPPORT_EMAIL: EmailStr

    # --- Security & Rate Limiting Settings ---
    MAX_FAILED_ATTEMPTS: int
    IP_PENALTY_DURATION: int
    FAILED_ATTEMPTS_WINDOW: int

    # --- Token Expiration Settings (in minutes) ---
    EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES: int
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int
    NEW_EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES: int
    OAUTH_STATE_TOKEN_EXPIRE_MINUTES: int

    # --- CORS Settings ---
    CORS_ALLOWED_ORIGINS: str

    # --- Calculated Properties ---
    @property
    def cors_origins(self) -> list[str]:
        """Parses the CORS_ALLOWED_ORIGINS string into a list."""
        if not self.CORS_ALLOWED_ORIGINS:
            return []
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def db_url(self) -> str:
        """
        Returns the appropriate database URL as a STRING based on the testing environment.
        """
        is_testing = os.getenv("PYTEST_CURRENT_TEST") is not None
        url_dsn = self.TEST_DATABASE_URL if is_testing else self.DATABASE_URL
        url_str = str(url_dsn)
        if self.DEBUG:
            print("🔍 Using DATABASE URL:", url_str)
            logger.debug(f"[CONFIG] Using DATABASE URL: {url_str}")
        return url_str

    @property
    def mail_templates_path(self) -> Path:
        """Returns the absolute path to the mail templates directory."""
        path = BASE_DIR / self.MAIL_TEMPLATES_DIR
        return path

    @property
    def redis_url(self) -> str:
        """Constructs Redis URL from individual components if needed elsewhere."""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


# ---------------------------------------------------
# Instantiate Settings Globally
# ---------------------------------------------------

if TYPE_CHECKING:
    # Stub settings for type hinting and editor assistance
    settings = Settings(
        # General Application Settings
        APP_NAME="",
        DEBUG=False,
        LOG_LEVEL="",
        BASE_URL="",
        # Database Settings
        DATABASE_URL="",
        TEST_DATABASE_URL="",
        # JWT Authentication Settings
        SECRET_KEY="",
        ALGORITHM="",
        ACCESS_TOKEN_EXPIRE_MINUTES=0,
        # OAuth2 - Google
        GOOGLE_CLIENT_ID="",
        GOOGLE_CLIENT_SECRET="",
        # Redis Settings
        REDIS_HOST="",
        REDIS_PORT=0,
        REDIS_DB=0,
        # AWS S3 Storage Settings
        AWS_ACCESS_KEY_ID="",
        AWS_SECRET_ACCESS_KEY="",
        AWS_REGION="",
        AWS_S3_BUCKET="",
        # Email Service Settings
        SENDGRID_API_KEY="",
        MAIL_FROM="",
        MAIL_FROM_NAME="",
        EMAILS_ENABLED=False,
        MAIL_TEMPLATES_DIR="",
        SUPPORT_EMAIL="",
        # Security & Rate Limiting Settings
        MAX_FAILED_ATTEMPTS=0,
        IP_PENALTY_DURATION=0,
        FAILED_ATTEMPTS_WINDOW=0,
        # Token Expiration Settings (in minutes)
        EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES=0,
        PASSWORD_RESET_TOKEN_EXPIRE_MINUTES=0,
        NEW_EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES=0,
        OAUTH_STATE_TOKEN_EXPIRE_MINUTES=0,
        # CORS Settings
        CORS_ALLOWED_ORIGINS="",
    )
else:
    settings = Settings()

# ---------------------------------------------------
# Post-Instantiation Validation
# ---------------------------------------------------
templates_path = settings.mail_templates_path
if not templates_path.is_dir():
    error_message = f"Email templates directory not found at resolved path: {templates_path} (expected value from MAIL_TEMPLATES_DIR in .env)"
    logger.error(error_message)
    raise ValueError(error_message)
else:
    logger.info(f"✅ Email templates directory found at: {templates_path}")
