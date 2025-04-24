"""
core/logging.py

Centralized logging configuration for the application.
- Uses RotatingFileHandler for file logs (1MB max, 5 backups)
- Logs to both console and logs/app.log
- Separate logs/error.log for ERROR and above
- Colored console logs if `colorlog` is installed
- Log level controlled via environment variable (LOG_LEVEL)

Should be initialized once early in app startup (e.g., in main.py)
"""

import os
import logging
from logging.config import dictConfig
from app.core.config import settings

# Check for colorlog availability
try:
    import colorlog

    COLORLOG_AVAILABLE = True
except ImportError:
    COLORLOG_AVAILABLE = False

# Create logs directory dynamically relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "..", "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_LEVEL = settings.LOG_LEVEL.upper()

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


def init_logging() -> None:
    """Initializes logging using the global LOGGING_CONFIG."""
    dictConfig(LOGGING_CONFIG)
