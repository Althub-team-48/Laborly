from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.models import User
from core.dependencies import get_db_session
from utils.logger import logger, log_system_action

router = APIRouter()

@router.post("/register")
def register_user(first_name: str, last_name: str, email: str, password: str, db: Session = Depends(get_db_session)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        logger.warning(f"Registration failed: Email {email} already exists")
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash=password,  # In production, hash the password
        role="Client",
        is_verified=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Log the action
    logger.info(f"User registered: {email}")
    log_system_action(
        db=db,
        action_type="USER_REGISTERED",
        details={"user_id": user.id, "email": user.email},
        user_id=user.id
    )
    
    return {"message": "User registered successfully", "user_id": user.id}