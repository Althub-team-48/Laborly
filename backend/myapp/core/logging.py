"""
backend/app/core/logging.py

Centralized Logging Configuration

Sets up structured logging for the application:
- Rotating file logs (1MB max per file, 5 backups)
- Separate error log file for ERROR and above
- Console logs with optional colorized output
- Logging level controlled via environment variable (LOG_LEVEL)

This module should be initialized once early in the app startup (e.g., in `main.py`).
"""

import importlib.util
import os
from logging.config import dictConfig

from myapp.core.config import settings

# ---------------------------------------------------
# Colorlog Availability Check
# ---------------------------------------------------
if importlib.util.find_spec("colorlog") is not None:
    COLORLOG_AVAILABLE = True
else:
    COLORLOG_AVAILABLE = False

# ---------------------------------------------------
# Log Directory Setup
# ---------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "..", "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# ---------------------------------------------------
# Global Logging Level
# ---------------------------------------------------
LOG_LEVEL = settings.LOG_LEVEL.upper()

# ---------------------------------------------------
# Logging Configuration Dictionary
# ---------------------------------------------------
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "[%(asctime)s] %(levelname)s [%(name)s] in %(module)s: %(message)s",
        },
        "color": (
            {
                "()": "colorlog.ColoredFormatter",
                "format": "%(log_color)s[%(asctime)s] %(levelname)s [%(name)s] in %(module)s: %(message)s",
                "log_colors": {
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "bold_red",
                },
            }
            if COLORLOG_AVAILABLE
            else {}
        ),
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "color" if COLORLOG_AVAILABLE else "default",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOG_DIR, "app.log"),
            "maxBytes": 1 * 1024 * 1024,  # 1MB
            "backupCount": 5,
            "formatter": "default",
            "encoding": "utf-8",
        },
        "error_file": {
            "class": "logging.FileHandler",
            "filename": os.path.join(LOG_DIR, "error.log"),
            "level": "ERROR",
            "formatter": "default",
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "uvicorn": {"level": "WARNING"},
        "sqlalchemy": {"level": "WARNING"},
    },
    "root": {
        "level": LOG_LEVEL,
        "handlers": ["console", "file", "error_file"],
    },
}

# ---------------------------------------------------
# Initialize Logging
# ---------------------------------------------------


def init_logging() -> None:
    """
    Initializes logging system based on the global LOGGING_CONFIG dictionary.
    """
    dictConfig(LOGGING_CONFIG)
