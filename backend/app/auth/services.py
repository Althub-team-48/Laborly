"""
auth_services.py

Handles authentication-related logic:
- Password hashing and verification
- JWT token generation
- Google OAuth2 login and callback handling
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Union

from jose import jwt
from passlib.context import CryptContext
from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config as StarletteConfig

from app.core.config import settings
from app.database.models import User
from app.database.enums import UserRole


# -----------------------------
# Password Hashing Utilities
# -----------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """
    Hashes a plaintext password using bcrypt.
    """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plaintext password against a hashed one.
    """
    return pwd_context.verify(plain_password, hashed_password)


# -----------------------------
# JWT Token Generation
# -----------------------------
def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    """
    Creates a signed JWT token with optional expiration.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# -----------------------------
# Google OAuth2 Setup
# -----------------------------
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


# -----------------------------
# Google OAuth Handlers
# -----------------------------
async def handle_google_login(request: Request):
    """
    Initiates the Google OAuth2 login flow.
    """
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


async def handle_google_callback(request: Request, db: Session):
    """
    Handles the Google OAuth2 callback:
    - Retrieves user info from Google
    - Auto-registers the user if not found
    - Issues a JWT access token
    """
    token = await oauth.google.authorize_access_token(request)
    resp = await oauth.google.get("userinfo", token=token)
    user_info = resp.json()

    email = user_info.get("email")
    first_name = user_info.get("given_name")
    last_name = user_info.get("family_name")

    user = db.query(User).filter(User.email == email).first()

    if not user:
        # Auto-register new Google user with CLIENT role
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            hashed_password=get_password_hash(os.urandom(16).hex()),
            role=UserRole.CLIENT,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    return RedirectResponse(url=f"/?token={access_token}")
