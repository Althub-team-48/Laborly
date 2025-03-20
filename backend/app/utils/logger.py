import logging
import os
from logging.handlers import RotatingFileHandler
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from ..database.models import SystemLog, AdminLog, ActionType
from fastapi import Request, Response

# Configure file-based logging
if not os.path.exists("logs"):
    os.makedirs("logs")

logger = logging.getLogger("LaborlyBackend")
logger.setLevel(logging.INFO)

handler = RotatingFileHandler("logs/laborly.log", maxBytes=1000000, backupCount=5)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

def log_system_action(db: Session, action_type: ActionType, details: dict, user_id: int = None):
    try:
        system_log = SystemLog(
            user_id=user_id,
            action_type=action_type,
            details=str(details),
            created_at=datetime.now(timezone.utc)
        )
        db.add(system_log)
        db.commit()
        logger.info(f"System action logged: {action_type.value} by user_id {user_id}")
    except Exception as e:
        logger.error(f"Failed to log system action to database: {str(e)}")

def log_admin_action(db: Session, admin_id: int, action_type: ActionType, details: dict):
    try:
        admin_log = AdminLog(
            admin_id=admin_id,
            action_type=action_type,
            details=str(details),
            created_at=datetime.now(timezone.utc)
        )
        db.add(admin_log)
        db.commit()
        logger.info(f"Admin action logged: {action_type.value} by admin_id {admin_id}")
    except Exception as e:
        logger.error(f"Failed to log admin action to database: {str(e)}")

async def log_request_response(request: Request, response: Response, db: Session = None):
    """
    Log HTTP request and response details.
    Args:
        request: The incoming HTTP request
        response: The outgoing HTTP response
        db: Optional database session for logging to SystemLog
    """
    # Extract request details
    method = request.method
    path = request.url.path
    client_ip = request.client.host
    user_id = None  # Placeholder for user_id (to be set after authentication in Phase 3)

    # Log request
    logger.info(f"Request: {method} {path} from {client_ip}")

    # Log response
    logger.info(f"Response: {method} {path} - Status {response.status_code}")

    # Log to database if a session is provided
    if db:
        details = {
            "method": method,
            "path": path,
            "client_ip": client_ip,
            "status_code": response.status_code
        }
        log_system_action(
            db=db,
            action_type=ActionType.LOGIN if "login" in path else ActionType.CREATE,
            details=details,
            user_id=user_id
        )