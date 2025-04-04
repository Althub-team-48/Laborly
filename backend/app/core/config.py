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
    app_name: str
    debug: bool = False
    database_url: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    class Config:
        env_file = ".env"  # Load variables from .env file


# Instantiate the settings for global use
settings = Settings()
