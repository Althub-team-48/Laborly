"""
[users] routes.py

Defines FastAPI routes for user-related operations:
- Registration and authentication
- Profile access and update
- Admin-only operations (list, get, delete users)
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session

from users.schemas import UserCreate, UserUpdate, UserOut, Token, UserList, LoginRequest
from users.service import UserService
from core.dependencies import get_db, get_current_user, get_admin_user
from core.security import create_access_token
from utils.logger import logger

router = APIRouter(prefix="/api/users", tags=["Users"])


def perform_login(email: str, password: str, db: Session) -> Token:
    """
    Shared login logic used by both JSON and form-based login endpoints.
    Authenticates the user and issues a JWT access token.
    """
    try:
        logger.info(f"Login attempt for email: {email}")
        user = UserService.authenticate_user(db, email, password)
        access_token = create_access_token(data={"sub": str(user.id)})
        logger.info(f"Login successful for {email}")
        return {"access_token": access_token, "token_type": "bearer"}
    except ValueError as e:
        logger.warning(f"Login failed for {email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Error during login for {email}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Registers a new user and returns the created user object.
    """
    try:
        return UserService.create_user(db, user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error registering user {user.email}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/login", response_model=Token)
def login_user_json(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticates user with JSON credentials and returns an access token.
    """
    return perform_login(login_data.email, login_data.password, db)


@router.post("/login-form", response_model=Token)
def login_user_form(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Authenticates user using form data (for OAuth2 password flow compatibility).
    The 'username' field is treated as the email.
    """
    return perform_login(username, password, db)


@router.get("/me", response_model=UserOut)
def get_current_user_profile(current_user: UserOut = Depends(get_current_user)):
    """
    Returns the currently authenticated user's profile.
    """
    return current_user


@router.put("/full-update/me", response_model=UserOut)
def update_current_user(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    """
    Fully updates the authenticated user's profile.
    """
    return UserService.update_user(db, current_user.id, user_update)


@router.patch("/partial-update/me", response_model=UserOut)
def patch_current_user(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    """
    Partially updates the authenticated user's profile.
    """
    return UserService.update_user(db, current_user.id, user_update)


@router.get("/all-users", response_model=UserList, dependencies=[Depends(get_admin_user)])
def list_users(db: Session = Depends(get_db)):
    """
    Returns a list of all users.
    Restricted to admin users.
    """
    users = UserService.get_all_users(db)
    return {"users": users}


@router.get("/get/{user_id}", response_model=UserOut, dependencies=[Depends(get_admin_user)])
def get_user(user_id: int, db: Session = Depends(get_db)):
    """
    Retrieves a user by ID.
    Restricted to admin users.
    """
    try:
        return UserService.get_user_by_id(db, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/delete/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_admin_user)])
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """
    Deletes a user by ID.
    Restricted to admin users.
    """
    try:
        UserService.delete_user(db, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
