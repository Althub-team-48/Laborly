"""
auth/routes.py

Handles authentication routes including:
- User registration and login via JSON or OAuth2
- Google OAuth2 login flow
- JWT token issuance and user logout handling
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Request,
    Header,
)
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from slowapi import Limiter

from app.auth.schemas import (
    LoginRequest,
    SignupRequest,
    AuthSuccessResponse,
    AuthUserResponse,
)
from app.auth.services import (
    verify_password,
    get_password_hash,
    create_access_token,
    handle_google_login,
    handle_google_callback,
)
from app.core.blacklist import blacklist_token
from app.core.config import settings
from app.core.dependencies import get_db, oauth2_scheme
from app.database.models import User
from app.database.enums import UserRole
from main import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------
# User Registration
# ---------------------------------------------------

@router.post("/signup", response_model=AuthSuccessResponse)
@limiter.limit("5/minute")
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    """
    Register a new user and return a JWT token with user info.
    """
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        logger.warning(f"[SIGNUP] Email already registered: {payload.email}")
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
    db.commit()
    db.refresh(new_user)

    logger.info(f"[SIGNUP] New user registered: {new_user.email} | Role: {new_user.role}")

    token = create_access_token({"sub": str(new_user.id), "role": new_user.role})
    return AuthSuccessResponse(
        access_token=token,
        user=AuthUserResponse.model_validate(new_user)
    )


# ---------------------------------------------------
# Login with JSON Credentials
# ---------------------------------------------------

@router.post("/login/json", response_model=AuthSuccessResponse)
@limiter.limit("10/minute")
def login_json(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate a user using JSON email/password.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        logger.warning(f"[LOGIN-JSON] Invalid login attempt: {payload.email}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    logger.info(f"[LOGIN-JSON] Success: {user.email} | Role: {user.role}")

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return AuthSuccessResponse(
        access_token=token,
        user=AuthUserResponse.model_validate(user)
    )


# ---------------------------------------------------
# Login with OAuth2 Form Fields
# ---------------------------------------------------

@router.post("/login/oauth", response_model=AuthSuccessResponse)
@limiter.limit("10/minute")
def login_oauth(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticate a user using OAuth2-compatible form fields.
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"[LOGIN-OAUTH2] Invalid login attempt: {form_data.username}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    logger.info(f"[LOGIN-OAUTH2] Success: {user.email} | Role: {user.role}")

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return AuthSuccessResponse(
        access_token=token,
        user=AuthUserResponse.model_validate(user)
    )


# ---------------------------------------------------
# Google OAuth2 Login Flow
# ---------------------------------------------------

@router.get("/google/login")
@limiter.limit("10/minute")
async def google_login(request: Request):
    """
    Start Google OAuth2 login redirect.
    """
    return await handle_google_login(request)


@router.get("/google/callback")
@limiter.limit("10/minute")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """
    Handle Google OAuth2 callback, register user if new,
    and return a JWT access token.
    """
    return await handle_google_callback(request, db)


# ---------------------------------------------------
# User Logout
# ---------------------------------------------------

@router.post("/logout")
@limiter.limit("20/minute")
def logout_user(token: str = Depends(oauth2_scheme)):
    """
    Logs out the current user by blacklisting their JWT.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            ttl = exp - int(datetime.utcnow().timestamp())
            blacklist_token(jti, ttl)
            logger.info(f"[LOGOUT] Token jti={jti} blacklisted for {ttl} seconds.")
        return {"detail": "Logout successful"}
    except JWTError:
        logger.warning("[LOGOUT] Invalid token on logout request.")
        raise HTTPException(status_code=400, detail="Invalid token")
