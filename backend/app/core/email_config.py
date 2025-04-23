"""
core/email_config.py

Mail connection configuration for sending emails via FastAPI-Mail.
Loads values from environment settings.
"""

from pathlib import Path
from fastapi_mail import ConnectionConfig
from pydantic import SecretStr

from app.core.config import settings

# Configuration for FastAPI-Mail using environment-based settings
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
