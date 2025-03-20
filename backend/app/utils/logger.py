import logging
import os
from logging.handlers import RotatingFileHandler
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from ..database.models import SystemLog, AdminLog, ActionType  

# Configure file-based logging
if not os.path.exists("logs"):
    os.makedirs("logs")

logger = logging.getLogger("LaborlyBackend")
logger.setLevel(logging.INFO)

handler = RotatingFileHandler("logs/laborly.log", maxBytes=1000000, backupCount=5)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

def log_system_action(db: Session, action_type: ActionType, details: dict, user_id: int = None):  # Updated action_type to ActionType enum
    try:
        system_log = SystemLog(
            user_id=user_id,
            action_type=action_type,
            details=str(details),
            created_at=datetime.now(timezone.utc)
        )
        db.add(system_log)
        db.commit()
        logger.info(f"System action logged: {action_type.value} by user_id {user_id}")  # Used action_type.value
    except Exception as e:
        logger.error(f"Failed to log system action to database: {str(e)}")  # Improved error message

def log_admin_action(db: Session, admin_id: int, action_type: ActionType, details: dict):  # Updated action_type to ActionType enum
    try:
        admin_log = AdminLog(
            admin_id=admin_id,
            action_type=action_type,
            details=str(details),
            created_at=datetime.now(timezone.utc)
        )
        db.add(admin_log)
        db.commit()
        logger.info(f"Admin action logged: {action_type.value} by admin_id {admin_id}")  # Used action_type.value
    except Exception as e:
        logger.error(f"Failed to log admin action to database: {str(e)}")  # Improved error message