"""
core/dependencies.py

Provides authentication and role-based access control (RBAC) dependencies for FastAPI:
- Extract and validate JWT tokens
- Check for blacklisted tokens (logout protection)
- Retrieve authenticated user from the database
- Restrict access based on allowed user roles
"""

import logging
from uuid import UUID
from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.auth.schemas import TokenPayload
from app.core.blacklist import is_token_blacklisted
from app.core.config import settings
from app.database.session import SessionLocal
from app.database.models import User
from app.database.enums import UserRole

# ----------------------------------------
# Logging Configuration
# ----------------------------------------
logger = logging.getLogger(__name__)

# ----------------------------------------
# OAuth2 Bearer Token Scheme
# ----------------------------------------
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login/oauth"  # OAuth2-compatible login endpoint
)


# ----------------------------------------
# DATABASE SESSION DEPENDENCY
# ----------------------------------------
def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a SQLAlchemy session and ensures proper teardown.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ----------------------------------------
# AUTHENTICATED USER DEPENDENCY
# ----------------------------------------
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Validates JWT token, checks blacklist, and retrieves user from the database.

    Raises:
        HTTPException 401 if token is invalid, expired, blacklisted, or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode JWT token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(**payload)

        # Check Redis token blacklist
        jti = payload.get("jti")
        if jti and is_token_blacklisted(jti):
            logger.warning(f"Token {jti} is blacklisted")
            raise credentials_exception

    except (JWTError, ValueError) as e:
        logger.warning(f"JWT decoding failed: {e}")
        raise credentials_exception

    # Fetch user from DB
    user = db.query(User).filter(User.id == token_data.sub).first()
    if not user:
        logger.warning(f"JWT valid but no user found: user_id={token_data.sub}")
        raise credentials_exception

    return user


# ----------------------------------------
# ROLE-RESTRICTED ACCESS DEPENDENCIES
# ----------------------------------------

def get_current_user_with_role(required_role: UserRole):
    """
    Returns a dependency that ensures the current user has a specific role.

    Usage:
        Depends(get_current_user_with_role(UserRole.ADMIN))
    """
    def role_dependency(user: User = Depends(get_current_user)) -> User:
        if user.role != required_role:
            logger.warning(
                f"Access denied: User {user.id} has role {user.role}, "
                f"required: {required_role}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied for role: {user.role}"
            )
        return user

    return role_dependency


def require_roles(*roles: UserRole):
    """
    Dependency to restrict access to users with any of the specified roles.

    Usage:
        Depends(require_roles(UserRole.CLIENT, UserRole.ADMIN))

    Raises:
        HTTPException 403 if the user's role is not among the allowed roles.
    """
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            logger.warning(
                f"Access denied: User {user.id} with role {user.role} "
                f"attempted to access restricted area (allowed: {roles})"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied for role: {user.role}"
            )
        return user

    return checker
