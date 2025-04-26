"""
core/dependencies.py

Provides authentication and role-based access control (RBAC) dependencies for FastAPI:
- Extract and validate JWT tokens
- Check for blacklisted tokens (logout protection)
- Retrieve authenticated user from the database
- Restrict access based on allowed user roles
"""

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, HTTPException, WebSocket, status
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

logger = logging.getLogger(__name__)

oauth2_scheme: OAuth2PasswordBearer = OAuth2PasswordBearer(tokenUrl="/auth/login/oauth")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Authenticate the current user based on the JWT access token.
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

    result = await db.execute(select(User).filter(User.id == token_data.sub))
    user = result.unique().scalar_one_or_none()

    if not user:
        logger.warning(f"JWT valid but no user found: user_id={token_data.sub}")
        raise credentials_exception

    return user


async def get_current_user_from_ws(websocket: WebSocket, db: AsyncSession) -> User:
    token = websocket.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        await websocket.close(code=1008)
        raise Exception("Missing or invalid token in WebSocket headers.")

    token = token.replace("Bearer ", "")
    return await get_current_user(token=token, db=db)


def get_current_user_with_role(required_role: UserRole) -> Callable[..., Coroutine[Any, Any, User]]:
    """
    Restrict access to users with a specific role.
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


def require_roles(*roles: UserRole) -> Callable[..., Coroutine[Any, Any, User]]:
    """
    Restrict access to users with any of the specified roles.
    """

    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            logger.warning(
                f"Access denied: User {user.id} with role {user.role} attempted access (allowed: {roles})"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied for role: {user.role}",
            )
        return user

    return checker
