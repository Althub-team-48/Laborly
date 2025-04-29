"""
backend/app/core/email_config.py

Email Configuration

Defines the mail connection settings for sending emails using FastAPI-Mail.
Values are dynamically loaded from environment variables.
"""

from pathlib import Path

from fastapi_mail import ConnectionConfig
from pydantic import SecretStr

from app.core.config import settings

# ---------------------------------------------------
# FastAPI-Mail Connection Configuration
# ---------------------------------------------------
conf: ConnectionConfig = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=SecretStr(settings.MAIL_PASSWORD),
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=settings.MAIL_USE_CREDENTIALS,
    VALIDATE_CERTS=settings.MAIL_VALIDATE_CERTS,
    TEMPLATE_FOLDER=Path(settings.MAIL_TEMPLATE_FOLDER),
)
