"""
auth/services.py

Handles authentication-related business logic:
- Password hashing and verification
- JWT token creation and logout
- Signup and login (JSON / OAuth2)
- Google OAuth2 login flow and callback
"""

import logging
import os
import random
import string
from datetime import datetime, timezone
from typing import Any, cast

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from jose import jwt, JWTError, ExpiredSignatureError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config as StarletteConfig

from app.auth.schemas import (
    AuthUserResponse,
    AuthSuccessResponse,
    LoginRequest,
    MessageResponse,
    SignupRequest,
    UserCreate,
)
from app.core.config import settings
from app.core.email import send_email_verification, send_welcome_email
from app.core.tokens import create_access_token, create_email_verification_token
from app.database.models import User
from app.core.blacklist import blacklist_token

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ------------------------------------------------
# Password Utilities
# ------------------------------------------------
def get_password_hash(password: str) -> str:
    return cast(str, pwd_context.hash(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return cast(bool, pwd_context.verify(plain_password, hashed_password))


def generate_strong_password(length: int = 12) -> str:
    if length < 8:
        raise ValueError("Password length must be at least 8 characters")

    required = [
        random.choice(string.ascii_uppercase),
        random.choice(string.ascii_lowercase),
        random.choice(string.digits),
        random.choice(string.punctuation),
    ]
    remaining = random.choices(
        string.ascii_letters + string.digits + string.punctuation, k=length - 4
    )
    password = required + remaining
    random.shuffle(password)
    return ''.join(password)


# ------------------------------------------------
# Signup with Email Verification
# ------------------------------------------------
async def signup_user(payload: SignupRequest, db: AsyncSession) -> MessageResponse:
    email_exists = (
        await db.execute(select(User).filter(User.email == payload.email))
    ).scalar_one_or_none()
    if email_exists:
        raise HTTPException(status_code=400, detail="Email already registered")

    phone_exists = (
        await db.execute(select(User).filter(User.phone_number == payload.phone_number))
    ).scalar_one_or_none()
    if phone_exists:
        raise HTTPException(status_code=400, detail="Phone number already in use")

    new_user = User(
        email=payload.email,
        phone_number=payload.phone_number,
        hashed_password=get_password_hash(payload.password),
        role=payload.role,
        first_name=payload.first_name,
        last_name=payload.last_name,
        is_verified=False,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    token = create_email_verification_token(str(new_user.id))
    await send_email_verification(new_user.email, token)

    return MessageResponse(
        detail="Registration successful. Please check your email to verify your account."
    )


# ------------------------------------------------
# Email Verification
# ------------------------------------------------
async def verify_email_token(token: str, db: AsyncSession) -> MessageResponse:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "email_verification":
            raise HTTPException(status_code=400, detail="Invalid token type")
    except ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Verification token has expired")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid verification token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid token payload")

    user = (await db.execute(select(User).filter(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_verified:
        return MessageResponse(detail="Your email has already been verified.")

    user.is_verified = True
    await db.commit()
    await send_welcome_email(user.email, user.first_name)

    return MessageResponse(detail="Your email has been successfully verified. You may now log in.")


# ------------------------------------------------
# Login (JSON and OAuth2)
# ------------------------------------------------
async def login_user_json(payload: LoginRequest, db: AsyncSession) -> AuthSuccessResponse:
    user = (await db.execute(select(User).filter(User.email == payload.email))).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Please verify your email before logging in.")

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return AuthSuccessResponse(access_token=token, user=AuthUserResponse.model_validate(user))


async def login_user_oauth(form_data: Any, db: AsyncSession) -> AuthSuccessResponse:
    user = (
        await db.execute(select(User).filter(User.email == form_data.username))
    ).scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Please verify your email before logging in.")

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return AuthSuccessResponse(access_token=token, user=AuthUserResponse.model_validate(user))


# ------------------------------------------------
# Logout
# ------------------------------------------------
def logout_user_token(token: str) -> dict[str, str]:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    jti = payload.get("jti")
    exp = payload.get("exp")

    if jti and exp:
        ttl = exp - int(datetime.now(timezone.utc).timestamp())
        blacklist_token(jti, ttl)
        logger.info(f"Token jti={jti} blacklisted for {ttl} seconds.")

    return {"detail": "Logout successful"}


# ------------------------------------------------
# Google OAuth2
# ------------------------------------------------
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


async def handle_google_login(request: Request) -> RedirectResponse:
    redirect_uri = request.url_for("google_callback")
    logger.info(f"Redirecting to Google OAuth2: {redirect_uri}")
    return cast(RedirectResponse, await oauth.google.authorize_redirect(request, redirect_uri))


async def handle_google_callback(request: Request, db: AsyncSession) -> RedirectResponse:
    token = await oauth.google.authorize_access_token(request)
    resp = await oauth.google.get("userinfo", token=token)
    user_info = resp.json()

    user = (
        await db.execute(select(User).filter(User.email == user_info.get("email")))
    ).scalar_one_or_none()

    if not user:
        password = generate_strong_password()
        hashed_password = get_password_hash(password)
        user_obj = UserCreate.from_google(user_info, hashed_password=hashed_password)

        user_fields = {c.key for c in inspect(User).mapper.column_attrs}
        user_data = {k: v for k, v in user_obj.model_dump().items() if k in user_fields}

        user = User(**user_data)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info(f"New user created via Google: {user.email}")

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    return RedirectResponse(url=f"/?token={access_token}")
