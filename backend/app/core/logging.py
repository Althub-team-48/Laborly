"""
core/logging.py

Defines centralized logging configuration for the application.
Sets up both console and file logging with consistent formatting.
"""

import logging
from logging.config import dictConfig

# Define logging settings
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "default": {
            "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "logs/app.log",
            "formatter": "default",
        },
    },

    "root": {
        "level": "INFO",
        "handlers": ["console", "file"],
    },
}


def init_logging() -> None:
    """
    Initialize application-wide logging using the predefined LOGGING_CONFIG.
    Call this early in the application lifecycle (e.g., main.py).
    """
    dictConfig(LOGGING_CONFIG)
