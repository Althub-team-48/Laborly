"""
backend/app/core/dependencies.py

Authentication and Authorization Dependencies

Provides authentication and role-based access control (RBAC) for FastAPI routes:
- Validates JWT tokens from Bearer header OR HttpOnly cookie
- Checks against blacklisted tokens (logout protection)
- Retrieves authenticated user from the database
- Restricts access based on user roles

Pagination Dependency:
- Provides reusable dependency for pagination (skip, limit).
"""

import logging
from collections.abc import Callable, Coroutine
from typing import Any, Annotated

from fastapi import Depends, HTTPException, Query, WebSocket, status, Cookie
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
# Keep the scheme for potential non-cookie auth, but disable auto_error
# If auto_error=True, it would raise 401 if header is missing, preventing cookie check
oauth2_scheme: OAuth2PasswordBearer = OAuth2PasswordBearer(
    tokenUrl="/auth/login/oauth", auto_error=False
)


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
    # Try Authorization header first (optional)
    token_header: Annotated[str | None, Depends(oauth2_scheme)] = None,
    # Fallback to reading from cookie named "access_token"
    token_cookie: Annotated[str | None, Cookie(alias="access_token")] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Authenticate the current user based on the provided JWT access token,
    checking Bearer header first, then HttpOnly cookie.

    Raises:
        HTTPException: 401 Unauthorized if authentication fails.
    """
    # Prioritize Authorization header, fallback to cookie
    token = token_header or token_cookie

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        # Only include WWW-Authenticate if no token was found at all
        # or potentially if Bearer specifically failed.
        headers={"WWW-Authenticate": "Bearer"} if token is None else None,
    )

    if token is None:
        logger.debug("[AUTH] No token found in Authorization header or access_token cookie.")
        raise credentials_exception

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(**payload)

        jti = payload.get("jti")
        if jti and is_token_blacklisted(jti):
            logger.warning(f"[AUTH] Blacklisted token detected: jti={jti}")
            raise credentials_exception

    except (JWTError, ValueError) as e:
        logger.warning(f"[AUTH] JWT decoding/validation failed: {e}")
        raise credentials_exception

    result = await db.execute(select(User).filter(User.id == token_data.sub))
    user = result.unique().scalar_one_or_none()

    if not user:
        logger.warning(f"[AUTH] JWT valid but no matching user found: user_id={token_data.sub}")
        raise credentials_exception

    # Optionally add checks for user active status etc. here if needed globally
    if not user.is_active:
        logger.warning(f"[AUTH] Authentication attempt by inactive user: {user.id}")
        raise credentials_exception

    logger.debug(
        f"[AUTH] User {user.id} authenticated successfully via {'Header' if token_header else 'Cookie'}."
    )
    return user


async def get_current_user_from_ws(
    websocket: WebSocket,
    db: AsyncSession,
) -> User:
    """
    Authenticate the current user from a WebSocket connection.
    Tries Authorization header first, then cookie.

    Raises:
        Exception: If token is missing or invalid.
    """
    token_header = websocket.headers.get("Authorization")
    token_cookie = websocket.cookies.get("access_token")  # Use the same key as set in service

    token = None
    if token_header and token_header.startswith("Bearer "):
        token = token_header.replace("Bearer ", "")
    elif token_cookie:
        token = token_cookie

    if not token:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION, reason="Authentication token missing."
        )
        raise Exception("Missing token in WebSocket headers or cookies.")

    # Use the same core get_current_user logic
    try:
        user = await get_current_user(
            token_header=token if token_header else None,
            token_cookie=token if token_cookie else None,
            db=db,
        )
        return user
    except HTTPException as e:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION, reason=f"Authentication failed: {e.detail}"
        )
        raise Exception(f"Authentication failed: {e.detail}")


# ---------------------------------------------------
# Authorization Functions (Role-Based) - No changes needed here
# ---------------------------------------------------


def get_current_user_with_role(required_role: UserRole) -> Callable[..., Coroutine[Any, Any, User]]:
    """
    Dependency to restrict access to users with a specific role.
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
