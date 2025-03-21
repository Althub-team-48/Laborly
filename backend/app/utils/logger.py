"""
logger.py

Initializes a rotating file logger for the application and defines a helper
to log system actions (e.g., CREATE, UPDATE, DELETE) into the database.
"""

import logging
from logging.handlers import RotatingFileHandler
from sqlalchemy.orm import Session
from database.models import SystemLog, ActionType
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path

# Log file path (e.g., backend/logs/laborly.log)
LOG_PATH = Path(__file__).resolve().parents[2] / "logs" / "laborly.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

# Configure rotating file logger
logger = logging.getLogger("Laborly")
logger.setLevel(logging.DEBUG)

handler = RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=5)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

logger.addHandler(handler)


def log_system_action(
    db: Session,
    user_id: Optional[int],
    action_type: ActionType,
    details: str
) -> None:
    """
    Records an action in the system logs table and writes to the log file.

    Args:
        db (Session): SQLAlchemy session object
        user_id (Optional[int]): ID of the user performing the action
        action_type (ActionType): Enum value representing the action
        details (str): Description of the action

    Raises:
        Exception: If logging to the database fails
    """
    try:
        log_entry = SystemLog(
            user_id=user_id,
            action_type=action_type,
            details=details,
            created_at=datetime.now(timezone.utc),
        )
        db.add(log_entry)
        db.commit()
        logger.info(f"System Log: {action_type.value} - {details}")
    except Exception as e:
        logger.error(f"Failed to log to database: {str(e)}")
        raise
