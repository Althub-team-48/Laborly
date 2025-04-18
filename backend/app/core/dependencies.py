"""
core/dependencies.py

Provides authentication and role-based access control (RBAC) dependencies for FastAPI:
- Extract and validate JWT tokens
- Check for blacklisted tokens (logout protection)
- Retrieve authenticated user from the database
- Restrict access based on allowed user roles
"""

import logging
from typing import AsyncGenerator, Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import TokenPayload
from app.core.blacklist import is_token_blacklisted
from app.core.config import settings
from app.database.enums import UserRole
from app.database.models import User
from app.database.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

# OAuth2 password bearer token scheme (for OAuth-based login)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login/oauth")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get a database session.
    """
    async with AsyncSessionLocal() as db:
        yield db


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Authenticate the current user based on the JWT access token.

    - Decodes the JWT token using the configured secret and algorithm.
    - Validates the token payload and checks if the token has been blacklisted.
    - Retrieves the user from the database using the user ID (sub) in the token.
    
    Raises:
        HTTPException: If the token is invalid, blacklisted, or the user is not found.

    Returns:
        User: The authenticated user object from the database.
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
            logger.warning(f"Token {jti} is blacklisted")
            raise credentials_exception

    except (JWTError, ValueError) as e:
        logger.warning(f"JWT decoding failed: {e}")
        raise credentials_exception

    user = (await db.execute(
        select(User).filter(User.id == token_data.sub))
    ).scalar_one_or_none()

    if not user:
        logger.warning(f"JWT valid but no user found: user_id={token_data.sub}")
        raise credentials_exception

    return user


def get_current_user_with_role(required_role: UserRole) -> Callable[[User], User]:
    """
    Restrict access to users with a specific role.

    - Wraps the `get_current_user` dependency to enforce role-based access control.
    - Verifies that the authenticated user has the required role.

    Args:
        required_role (UserRole): The exact role required to access the route.

    Returns:
        Callable: A dependency function that checks the user's role and returns the user if authorized.

    Raises:
        HTTPException: If the user does not have the required role.
    """

    async def role_dependency(user: User = Depends(get_current_user)) -> User:
        if user.role != required_role:
            logger.warning(
                f"Access denied: User {user.id} has role {user.role}, required: {required_role}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied for role: {user.role}",
            )
        return user

    return role_dependency


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    """
    Dependency that restricts access to users with any of the specified roles.

    This is a flexible role-based access control (RBAC) utility.
    Use in route dependencies to allow access only to users with certain roles.

    Example:
        @app.get("/admin-or-manager")
        async def secure_route(user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))):
            ...

    Args:
        *roles (UserRole): One or more allowed roles.

    Raises:
        HTTPException: 403 Forbidden if user does not have one of the allowed roles.

    Returns:
        Callable: A FastAPI dependency that returns the authenticated user if role is allowed.
    """

    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            logger.warning(
                f"Access denied: User {user.id} with role {user.role} "
                f"attempted to access restricted area (allowed: {roles})"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied for role: {user.role}",
            )
        return user

    return checker