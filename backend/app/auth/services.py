"""
auth/services.py

Handles authentication-related logic:
- Password hashing and verification
- JWT token generation
- Google OAuth2 login and callback handling
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Union

from jose import jwt
from passlib.context import CryptContext
from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy.inspection import inspect
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config as StarletteConfig

from app.core.config import settings
from app.database.models import User
from app.database.enums import UserRole
from app.auth.schemas import UserCreate

logger = logging.getLogger(__name__)

# -----------------------------
# Password Hashing Utilities
# -----------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    """
    logger.debug("Hashing password")
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a hashed hash.
    """
    logger.debug("Verifying password")
    return pwd_context.verify(plain_password, hashed_password)

# -----------------------------
# JWT Token Generation
# -----------------------------
def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    """
    Create a signed JWT token with an optional expiration.
    """
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {**data, "exp": expire}
    logger.info(f"Issuing access token for subject={data.get('sub')} exp={expire}")
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

# -----------------------------
# Google OAuth2 Configuration
# -----------------------------
starlette_config = StarletteConfig(environ=os.environ)
oauth = OAuth(starlette_config)

oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    client_kwargs={"scope": "openid email profile"},
    api_base_url="https://www.googleapis.com/oauth2/v3/"
)

# -----------------------------
# Google OAuth2 Handlers
# -----------------------------
async def handle_google_login(request: Request):
    """
    Initiate Google OAuth2 login flow.
    """
    redirect_uri = request.url_for("google_callback")
    logger.info(f"Redirecting to Google OAuth2: {redirect_uri}")
    return await oauth.google.authorize_redirect(request, redirect_uri)

async def handle_google_callback(request: Request, db: Session):
    """
    Handle the callback from Google OAuth2:
    - Retrieve user info
    - Register user if not found
    - Return access token
    """
    logger.info("Handling Google OAuth2 callback")
    token = await oauth.google.authorize_access_token(request)
    resp = await oauth.google.get("userinfo", token=token)
    user_info = resp.json()

    logger.info(f"Google profile retrieved: {user_info.get('email')}")
    user = db.query(User).filter(User.email == user_info.get("email")).first()

    if not user:
        logger.info("Registering new Google user...")
        user_obj = UserCreate.from_google(user_info)
        user_fields = {c.key for c in inspect(User).mapper.column_attrs}
        user_data = {k: v for k, v in user_obj.dict().items() if k in user_fields}

        user = User(**user_data)
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"New user created via Google OAuth2: user_id={user.id}")
    else:
        logger.info(f"Google user logged in: user_id={user.id}")

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    logger.info(f"Access token issued for Google user: user_id={user.id}")
    return RedirectResponse(url=f"/?token={access_token}")
