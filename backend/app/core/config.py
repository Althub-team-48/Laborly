"""
core/config.py

Loads and manages application configuration from environment variables.
Utilizes Pydantic BaseSettings for type validation and `.env` support.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application-wide settings loaded from environment variables.
    """
    APP_NAME: str
    DEBUG: bool = False
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

    class Config:
        env_file = ".env"  # Load variables from .env file


# Instantiate the settings for global use
settings = Settings()
