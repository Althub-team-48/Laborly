"""
core/logging.py

Defines centralized logging configuration for the application.
Sets up both console and file logging with consistent formatting and log rotation readiness.

- Writes logs to console (stdout) and file at logs/app.log
- Should be initialized once early in app startup (e.g., in main.py)
"""

import os
import logging
from logging.config import dictConfig

# Ensure the logs directory exists
os.makedirs("logs", exist_ok=True)

# Define centralized logging settings
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
            "encoding": "utf-8",
        },
    },

    "root": {
        "level": "INFO",
        "handlers": ["console", "file"],
    },
}


def init_logging() -> None:
    """
    Initializes logging using the global LOGGING_CONFIG.

    - Must be called once during app startup.
    - Creates 'logs/' directory if it does not exist.
    - Writes logs to both stdout and logs/app.log.
    """
    dictConfig(LOGGING_CONFIG)
