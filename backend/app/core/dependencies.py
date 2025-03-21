"""
dependencies.py

This file defines FastAPI dependency functions used throughout the application:
- Provides a database session (`get_db`)
- Retrieves the currently authenticated user (`get_current_user`)
- Ensures only admin users can access certain routes (`get_admin_user`)
"""

from typing import Generator

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.config import SessionLocal
from core.security import oauth2_scheme, decode_access_token
from database.models import User, UserRole  # Ensure UserRole enum is imported
from utils.logger import logger


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get a SQLAlchemy database session.
    Ensures that the session is closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to retrieve the currently authenticated user based on the token.
    Raises an HTTP 401 error if the token is invalid or the user is not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    user_id: str = payload.get("sub")

    if user_id is None:
        logger.warning("No user_id in token payload")
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        logger.warning(f"User not found for id: {user_id}")
        raise credentials_exception

    return user


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to ensure the current user is an admin.
    Raises an HTTP 403 error if the user does not have admin privileges.
    """
    if current_user.role != UserRole.ADMIN:
        logger.warning(f"Unauthorized access attempt by {current_user.email}")
        raise HTTPException(status_code=403, detail="Admin access required")

    return current_user
