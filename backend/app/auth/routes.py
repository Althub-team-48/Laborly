"""
auth/routes.py

Handles authentication routes including:
- User registration and login via JSON or OAuth2
- Google OAuth2 login flow
- JWT token issuance and user logout handling
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import (
    LoginRequest,
    SignupRequest,
    AuthSuccessResponse,
)
from app.auth.services import (
    signup_user,
    login_user_json,
    login_user_oauth,
    handle_google_login,
    handle_google_callback,
    logout_user_token,
)
from app.core.dependencies import get_db, oauth2_scheme
from app.core.limiter import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


@router.post("/signup", response_model=AuthSuccessResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def signup(request: Request, payload: SignupRequest, db: AsyncSession = Depends(get_db)):
    return await signup_user(payload, db)


@router.post("/login/json", response_model=AuthSuccessResponse, status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def login_json(request: Request, payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await login_user_json(payload, db)


@router.post("/login/oauth", response_model=AuthSuccessResponse, status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def login_oauth(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    return await login_user_oauth(form_data, db)


@router.get("/google/login", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def google_login(request: Request):
    return await handle_google_login(request)


@router.get("/google/callback", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def google_callback(request: Request, db: AsyncSession = Depends(get_db)):
    return await handle_google_callback(request, db)


@router.post("/logout", status_code=status.HTTP_200_OK, response_model=dict)
@limiter.limit("20/minute")
async def logout_user(request: Request, token: str = Depends(oauth2_scheme)):
    try:
        return logout_user_token(token)
    except JWTError:
        logger.warning("[LOGOUT] Invalid token on logout request.")
        raise HTTPException(status_code=400, detail="Invalid token")
