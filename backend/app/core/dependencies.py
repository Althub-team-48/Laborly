"""
backend/app/core/dependencies.py

Authentication and Authorization Dependencies

Provides authentication and role-based access control (RBAC) for FastAPI routes:
- Validates JWT tokens
- Checks against blacklisted tokens (logout protection)
- Retrieves authenticated user from the database
- Restricts access based on user roles

Pagination Dependency:
- Provides reusable dependency for pagination (skip, limit).
"""

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, HTTPException, Query, WebSocket, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import TokenPayload
from app.core.blacklist import is_token_blacklisted
from app.core.config import settings
from app.database.enums import UserRole
from app.database.models import User
from app.database.session import get_db

# ---------------------------------------------------
# Logger Configuration
# ---------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------
# OAuth2 Configuration
# ---------------------------------------------------
oauth2_scheme: OAuth2PasswordBearer = OAuth2PasswordBearer(tokenUrl="/auth/login/oauth")


# ---------------------------------------------------
# Pagination Dependency
# ---------------------------------------------------
class PaginationParams:
    """
    Dependency that provides pagination parameters from query parameters.
    """

    def __init__(
        self,
        skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
        limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    ):
        self.skip = skip
        self.limit = limit


# ---------------------------------------------------
# Authentication Functions
# ---------------------------------------------------


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Authenticate the current user based on the provided JWT access token.

    Raises:
        HTTPException: 401 Unauthorized if authentication fails.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(**payload)

        jti = payload.get("jti")
        if jti and is_token_blacklisted(jti):
            logger.warning(f"[AUTH] Blacklisted token detected: jti={jti}")
            raise credentials_exception

    except (JWTError, ValueError) as e:
        logger.warning(f"[AUTH] JWT decoding failed: {e}")
        raise credentials_exception

    result = await db.execute(select(User).filter(User.id == token_data.sub))
    user = result.unique().scalar_one_or_none()

    if not user:
        logger.warning(f"[AUTH] JWT valid but no matching user found: user_id={token_data.sub}")
        raise credentials_exception

    return user


async def get_current_user_from_ws(
    websocket: WebSocket,
    db: AsyncSession,
) -> User:
    """
    Authenticate the current user from a WebSocket connection.

    Raises:
        Exception: If token is missing or invalid.
    """
    token = websocket.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise Exception("Missing or invalid token in WebSocket headers.")

    token = token.replace("Bearer ", "")
    return await get_current_user(token=token, db=db)


# ---------------------------------------------------
# Authorization Functions (Role-Based)
# ---------------------------------------------------


def get_current_user_with_role(required_role: UserRole) -> Callable[..., Coroutine[Any, Any, User]]:
    """
    Dependency to restrict access to users with a specific role.

    Args:
        required_role (UserRole): The role required to access the route.

    Returns:
        Callable that validates the current user's role.
    """

    async def role_dependency(user: User = Depends(get_current_user)) -> User:
        if user.role != required_role:
            logger.warning(
                f"[RBAC] Access denied: User {user.id} role={user.role}, required={required_role}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied for role: {user.role}",
            )
        return user

    return role_dependency


def require_roles(*roles: UserRole) -> Callable[..., Coroutine[Any, Any, User]]:
    """
    Dependency to restrict access to users having any of the specified roles.

    Args:
        roles (UserRole): One or more allowed user roles.

    Returns:
        Callable that validates if user role is among the allowed roles.
    """

    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            logger.warning(
                f"[RBAC] Access denied: User {user.id} with role {user.role} attempted access (allowed roles: {roles})"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied for role: {user.role}",
            )
        return user

    return checker
