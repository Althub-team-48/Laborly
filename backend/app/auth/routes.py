"""
auth/routes.py

Handles authentication routes including:
- User registration and login via JSON or OAuth2
- Google OAuth2 login flow
- JWT token issuance and user response formatting
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth.schemas import (
    LoginRequest,
    SignupRequest,
    TokenResponse,
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
from app.core.dependencies import get_db
from app.database.models import User
from app.database.enums import UserRole

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ---------------------------------------
# User Signup
# ---------------------------------------
@router.post("/signup", response_model=AuthSuccessResponse)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    """
    Registers a new user and returns an access token + user info.
    """
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        role=payload.role,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token({"sub": str(new_user.id), "role": new_user.role})
    return AuthSuccessResponse(
        access_token=access_token,
        user=AuthUserResponse.model_validate(new_user)
    )

# ---------------------------------------
# Login via JSON Payload
# ---------------------------------------
@router.post("/login/json", response_model=AuthSuccessResponse)
def login_json(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticates a user using JSON credentials.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    return AuthSuccessResponse(
        access_token=access_token,
        user=AuthUserResponse.model_validate(user)
    )

# ---------------------------------------
# Login via OAuth2 Password Flow
# ---------------------------------------
@router.post("/login/oauth", response_model=AuthSuccessResponse)
def login_oauth(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticates user via OAuth2-compatible form fields.
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    return AuthSuccessResponse(
        access_token=access_token,
        user=AuthUserResponse.model_validate(user)
    )

# ---------------------------------------
# Google OAuth2 Login Flow
# ---------------------------------------
@router.get("/google/login")
async def google_login(request: Request):
    """
    Starts the Google OAuth2 login redirect.
    """
    return await handle_google_login(request)

@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """
    Handles Google's OAuth2 callback, registers user if needed, and issues a JWT.
    """
    return await handle_google_callback(request, db)
