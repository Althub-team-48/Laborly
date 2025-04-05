"""
core/dependencies.py

Authentication and role-based access control (RBAC) dependencies for FastAPI routes:
- Extract and validate JWT access tokens
- Fetch the current user from the database
- Restrict access based on user roles
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from uuid import UUID
from typing import Generator

from app.core.config import settings
from app.database.session import SessionLocal
from app.auth.schemas import TokenPayload
from app.database.models import User
from app.database.enums import UserRole


# --------------------------------------
# OAuth2 password bearer token scheme
# --------------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login/oauth")  # Points to the form-based login endpoint


# -------------------------
# DATABASE SESSION DEPENDENCY
# -------------------------
def get_db() -> Generator[Session, None, None]:
    """
    Dependency to provide a database session.
    Automatically closes session after request lifecycle.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------
# CURRENT USER DEPENDENCY
# -------------------------
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Validates the JWT token and retrieves the authenticated user from the database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(**payload)
    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == token_data.sub).first()
    if not user:
        raise credentials_exception
    return user


# -------------------------
# ROLE-BASED ACCESS DEPENDENCY
# -------------------------
def get_current_user_with_role(required_role: UserRole):
    """
    Returns a dependency that ensures the current user has a specific role.
    Usage: Depends(get_current_user_with_role(UserRole.ADMIN))
    """
    def role_dependency(user: User = Depends(get_current_user)) -> User:
        if user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied for role: {user.role}"
            )
        return user
    return role_dependency

def require_roles(*roles: UserRole):
    """
    Dependency that restricts access to users with specified roles.

    Usage:
    - Attach to any route via Depends(require_roles(...)).
    - Accepts one or more UserRole values.

    Raises:
        HTTPException 403 if the user's role is not in the allowed roles.
    """
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied for role: {user.role}"
            )
        return user

    return checker
