"""
auth/services.py

Handles authentication-related business logic:
- Password hashing and verification
- JWT token creation and logout
- Signup, login (JSON/OAuth2)
- Google OAuth2 login flow
"""

import logging
import uuid
import os
from datetime import datetime, timedelta, timezone
from typing import Union

from fastapi import HTTPException, Request, status
from fastapi.responses import RedirectResponse
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config as StarletteConfig

from app.auth.schemas import (
    SignupRequest,
    LoginRequest,
    AuthUserResponse,
    AuthSuccessResponse,
    UserCreate,
)
from app.database.models import User
from app.database.enums import UserRole
from app.core.config import settings

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# -------------------------------
# Password Utilities
# -------------------------------

def get_password_hash(password: str) -> str:
    """Generate a hashed version of the password."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify if the plain password matches the hashed one."""
    return pwd_context.verify(plain_password, hashed_password)

# -------------------------------
# JWT Access Token
# -------------------------------

def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    """Create a JWT access token with expiration and JTI."""
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    jti = str(uuid.uuid4())
    to_encode = {**data, "exp": expire, "jti": jti}
    logger.info(f"Issuing token for sub={data.get('sub')} exp={expire} jti={jti}")
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

# -------------------------------
# Signup
# -------------------------------

async def signup_user(payload: SignupRequest, db: AsyncSession) -> AuthSuccessResponse:
    """Create a new user and return a JWT upon success."""
    existing_user = (await db.execute(select(User).filter(User.email == payload.email))).scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=payload.email,
        phone_number=payload.phone_number,
        hashed_password=get_password_hash(payload.password),
        role=payload.role,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    token = create_access_token({"sub": str(new_user.id), "role": new_user.role})
    return AuthSuccessResponse(access_token=token, user=AuthUserResponse.model_validate(new_user))

# -------------------------------
# Login (JSON)
# -------------------------------

async def login_user_json(payload: LoginRequest, db: AsyncSession) -> AuthSuccessResponse:
    """Login using email/password from JSON."""
    user = (await db.execute(select(User).filter(User.email == payload.email))).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return AuthSuccessResponse(access_token=token, user=AuthUserResponse.model_validate(user))

# -------------------------------
# Login (OAuth2)
# -------------------------------

async def login_user_oauth(form_data, db: AsyncSession) -> AuthSuccessResponse:
    """Login using OAuth2 form (username = email)."""
    user = (await db.execute(select(User).filter(User.email == form_data.username))).scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return AuthSuccessResponse(access_token=token, user=AuthUserResponse.model_validate(user))

# -------------------------------
# Logout
# -------------------------------

def logout_user_token(token: str) -> dict:
    """Logout user by blacklisting the token using its JTI."""
    from app.core.blacklist import blacklist_token

    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    jti = payload.get("jti")
    exp = payload.get("exp")
    if jti and exp:
        ttl = exp - int(datetime.now(timezone.utc).timestamp())
        blacklist_token(jti, ttl)
        logger.info(f"Token jti={jti} blacklisted for {ttl} seconds.")
    return {"detail": "Logout successful"}

# -------------------------------
# Google OAuth2
# -------------------------------

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

async def handle_google_login(request: Request):
    """Redirect user to Google OAuth2 login screen."""
    redirect_uri = request.url_for("google_callback")
    logger.info(f"Redirecting to Google: {redirect_uri}")
    return await oauth.google.authorize_redirect(request, redirect_uri)

async def handle_google_callback(request: Request, db: AsyncSession):
    """Handle the callback after Google authentication."""
    token = await oauth.google.authorize_access_token(request)
    resp = await oauth.google.get("userinfo", token=token)
    user_info = resp.json()

    logger.info(f"Google profile retrieved: {user_info.get('email')}")
    user = (await db.execute(select(User).filter(User.email == user_info.get("email")))).scalar_one_or_none()

    if not user:
        # New user - create one
        uuid_password = str(uuid.uuid4())
        hashed_password = get_password_hash(uuid_password)
        user_obj = UserCreate.from_google(user_info, hashed_password=hashed_password)

        user_fields = {c.key for c in inspect(User).mapper.column_attrs}
        user_data = {k: v for k, v in user_obj.dict().items() if k in user_fields}

        user = User(**user_data)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info(f"New Google user created: user_id={user.id}")
    else:
        logger.info(f"Returning Google user: user_id={user.id}")

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    return RedirectResponse(url=f"/?token={access_token}")
