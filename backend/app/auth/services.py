"""
auth/services.py

Handles authentication-related business logic:
- Password hashing and verification
- JWT access token generation with expiration and jti
- Google OAuth2 login and callback handling
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Union
from uuid import uuid4

from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, Request, status
from fastapi.responses import RedirectResponse
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect
from starlette.config import Config as StarletteConfig

from app.auth.schemas import UserCreate
from app.core.config import settings
from app.database.enums import UserRole
from app.database.models import User

logger = logging.getLogger(__name__)

# Password encryption context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------
# Password hashing and verification
# ---------------------------------------

def get_password_hash(password: str) -> str:
    """
    Hash a plain password using bcrypt.
    """
    logger.debug("Hashing password")
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against its hashed version.
    """
    logger.debug("Verifying password")
    return pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------
# JWT Access Token Creation
# ---------------------------------------

def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    """
    Generate a signed JWT access token with an expiration and unique JTI.
    """
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    jti = str(uuid4())

    to_encode = {
        **data,
        "exp": expire,
        "jti": jti,
    }

    logger.info(f"Issuing access token for subject={data.get('sub')} exp={expire} jti={jti}")
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ---------------------------------------
# Google OAuth2 Configuration
# ---------------------------------------

starlette_config = StarletteConfig(environ=os.environ)

oauth = OAuth(starlette_config)
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    client_kwargs={"scope": "openid email profile"},
    api_base_url="https://www.googleapis.com/oauth2/v3/",
)


# ---------------------------------------
# Google OAuth2 Handlers
# ---------------------------------------

async def handle_google_login(request: Request):
    """
    Initiates the OAuth2 login flow by redirecting the user to Google.
    """
    redirect_uri = request.url_for("google_callback")
    logger.info(f"Redirecting to Google OAuth2: {redirect_uri}")
    return await oauth.google.authorize_redirect(request, redirect_uri)


async def handle_google_callback(request: Request, db: AsyncSession):
    """
    Handles Google OAuth2 callback, registers new user if not found,
    then issues and redirects with a JWT token.
    """
    logger.info("Handling Google OAuth2 callback")

    token = await oauth.google.authorize_access_token(request)
    resp = await oauth.google.get("userinfo", token=token)
    user_info = resp.json()

    logger.info(f"Google profile retrieved: {user_info.get('email')}")

    user = (
        await db.execute(select(User).filter(User.email == user_info.get("email")))
    ).scalar_one_or_none()

    if not user:
        logger.info("Registering new Google user...")
        user_obj = UserCreate.from_google(user_info)
        user_fields = {c.key for c in inspect(User).mapper.column_attrs}
        user_data = {k: v for k, v in user_obj.dict().items() if k in user_fields}

        user = User(**user_data)
        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info(f"New user created via Google OAuth2: user_id={user.id}")
    else:
        logger.info(f"Google user logged in: user_id={user.id}")

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    logger.info(f"Access token issued for Google user: user_id={user.id}")
    return RedirectResponse(url=f"/?token={access_token}")
