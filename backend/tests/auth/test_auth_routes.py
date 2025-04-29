"""
tests/auth/test_auth_routes.py

Unit tests for auth/routes.py with both success and failure scenarios
- Mocks service logic
- Uses Pytest fixtures for DRY code
- Uses httpx AsyncClient for integration tests
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import status, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from myapp.auth.schemas import (
    SignupRequest,
    MessageResponse,
    LoginRequest,
    AuthSuccessResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UpdateEmailRequest,
)
from myapp.database.enums import UserRole
from myapp.database.models import User


# =====================
# --- Signup Tests ---
# =====================
@pytest.mark.asyncio
@patch("app.auth.routes.signup_user", new_callable=AsyncMock)
async def test_signup_success(
    mock_signup: AsyncMock, async_client: AsyncClient, override_get_db: None
) -> None:
    """Test successful user signup"""
    mock_signup.return_value = MessageResponse(
        detail="Registration successful. Please check your email to verify your account."
    )
    payload = SignupRequest(
        email="test.user.signup@example.com",
        phone_number="0987654321",
        password="StrongPassword@123",
        first_name="Test",
        last_name="User",
        role=UserRole.CLIENT,
    ).model_dump()
    response = await async_client.post("/auth/signup", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    assert (
        response.json()["detail"]
        == "Registration successful. Please check your email to verify your account."
    )
    mock_signup.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.auth.routes.signup_user", new_callable=AsyncMock)
async def test_signup_duplicate_email(
    mock_signup: AsyncMock, async_client: AsyncClient, override_get_db: None
) -> None:
    """Test signup failure due to duplicate email"""
    mock_signup.side_effect = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
    )
    payload = SignupRequest(
        email="existing@example.com",
        phone_number="1234567890",
        password="StrongPassword@123",
        first_name="Jane",
        last_name="Doe",
        role=UserRole.CLIENT,
    ).model_dump()
    response = await async_client.post("/auth/signup", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Email already registered"
    mock_signup.assert_awaited_once()


# =========================
# --- Login JSON Tests ---
# =========================
@pytest.mark.asyncio
@patch("app.auth.routes.login_user_json", new_callable=AsyncMock)
async def test_login_json_success(
    mock_login: AsyncMock,
    fake_auth_success_response: AuthSuccessResponse,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    mock_login.return_value = fake_auth_success_response
    payload = LoginRequest(email="user@example.com", password="StrongPassword@123").model_dump()
    response = await async_client.post("/auth/login/json", json=payload)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["access_token"] == fake_auth_success_response.access_token
    assert response.json()["user"]["email"] == fake_auth_success_response.user.email
    mock_login.assert_awaited_once()
    call_args, call_kwargs = mock_login.call_args
    assert call_args[0].email == payload["email"]
    assert call_args[0].password == payload["password"]
    assert isinstance(call_args[1], AsyncMock)
    assert isinstance(call_args[2], str)


@pytest.mark.asyncio
@patch("app.auth.routes.login_user_json", new_callable=AsyncMock)
async def test_login_json_invalid_credentials(
    mock_login: AsyncMock, async_client: AsyncClient, override_get_db: None
) -> None:
    mock_login.side_effect = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
    )
    payload = LoginRequest(email="user@example.com", password="WrongPassword@1").model_dump()
    response = await async_client.post("/auth/login/json", json=payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid credentials"
    mock_login.assert_awaited_once()


# ================================
# --- Login OAuth2 Form Tests ---
# ================================
@pytest.mark.asyncio
@patch("app.auth.routes.login_user_oauth", new_callable=AsyncMock)
async def test_login_oauth_success(
    mock_oauth_login: AsyncMock,
    fake_auth_success_response: AuthSuccessResponse,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    mock_oauth_login.return_value = fake_auth_success_response
    form_data = {"username": "user@example.com", "password": "StrongPassword@123"}
    response = await async_client.post("/auth/login/oauth", data=form_data)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["access_token"] == fake_auth_success_response.access_token
    assert response.json()["user"]["email"] == fake_auth_success_response.user.email
    mock_oauth_login.assert_awaited_once()
    call_args, call_kwargs = mock_oauth_login.call_args
    assert isinstance(call_args[0], OAuth2PasswordRequestForm)
    assert call_args[0].username == form_data["username"]
    assert call_args[0].password == form_data["password"]
    assert isinstance(call_args[1], AsyncMock)
    assert isinstance(call_args[2], str)


@pytest.mark.asyncio
@patch("app.auth.routes.login_user_oauth", new_callable=AsyncMock)
async def test_login_oauth_invalid_credentials(
    mock_oauth_login: AsyncMock, async_client: AsyncClient, override_get_db: None
) -> None:
    mock_oauth_login.side_effect = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
    )
    form_data = {"username": "user@example.com", "password": "WrongPassword@1"}
    response = await async_client.post("/auth/login/oauth", data=form_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid credentials"
    mock_oauth_login.assert_awaited_once()


# ====================
# --- Logout Test ---
# ====================
@pytest.mark.asyncio
@patch("app.auth.routes.logout_user_token")
async def test_logout_user(
    mock_logout_service: MagicMock,
    mock_current_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    mock_logout_service.return_value = {"detail": "Logout successful"}
    headers = {"Authorization": "Bearer dummy-token-for-logout"}
    response = await async_client.post("/auth/logout", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["detail"] == "Logout successful"
    mock_logout_service.assert_called_once_with("dummy-token-for-logout")


# =================================
# --- Email Verification Tests ---
# =================================
@pytest.mark.asyncio
@patch("app.auth.routes.verify_email_token", new_callable=AsyncMock)
async def test_verify_email_success(
    mock_verify: AsyncMock, async_client: AsyncClient, override_get_db: None
) -> None:
    mock_verify.return_value = MessageResponse(detail="Your email has been successfully verified.")
    verification_token = "valid-verification-token"
    response = await async_client.get(f"/auth/verify-email?token={verification_token}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["detail"] == "Your email has been successfully verified."
    mock_verify.assert_awaited_once()
    call_args, call_kwargs = mock_verify.call_args
    assert call_args[0] == verification_token
    assert isinstance(call_args[1], AsyncMock)


@pytest.mark.asyncio
@patch("app.auth.routes.verify_email_token", new_callable=AsyncMock)
async def test_verify_email_invalid_token(
    mock_verify: AsyncMock, async_client: AsyncClient, override_get_db: None
) -> None:
    mock_verify.side_effect = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token."
    )
    invalid_token = "invalid-or-expired-token"
    response = await async_client.get(f"/auth/verify-email?token={invalid_token}")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Invalid token."
    mock_verify.assert_awaited_once()
    call_args, call_kwargs = mock_verify.call_args
    assert call_args[0] == invalid_token
    assert isinstance(call_args[1], AsyncMock)


# =============================================
# --- Request New Verification Email Tests ---
# =============================================
@pytest.mark.asyncio
@patch("app.auth.routes.request_new_verification_email", new_callable=AsyncMock)
async def test_request_verification_email_success(
    mock_request_verify: AsyncMock, async_client: AsyncClient, override_get_db: None
) -> None:
    """Test successfully requesting a new verification email"""
    test_email = "unverified@example.com"
    mock_request_verify.return_value = MessageResponse(
        detail="If an account with that email exists and requires verification, a new verification link has been sent."
    )

    response = await async_client.post(f"/auth/request-verification-email/{test_email}")

    assert response.status_code == status.HTTP_200_OK
    assert (
        response.json()["detail"]
        == "If an account with that email exists and requires verification, a new verification link has been sent."
    )
    # Assert mock called with email and db session
    mock_request_verify.assert_awaited_once()
    call_args, call_kwargs = mock_request_verify.call_args
    assert call_args[0] == test_email
    assert isinstance(call_args[1], AsyncMock)


# ====================================
# --- Forgot/Reset Password Tests ---
# ====================================
@pytest.mark.asyncio
@patch("app.auth.routes.request_password_reset", new_callable=AsyncMock)
async def test_forgot_password_success(
    mock_forgot_pw: AsyncMock, async_client: AsyncClient, override_get_db: None
) -> None:
    """Test successfully requesting a password reset"""
    mock_forgot_pw.return_value = MessageResponse(
        detail="If an account with that email exists and is verified, a password reset link has been sent."
    )
    payload = ForgotPasswordRequest(email="user@example.com").model_dump()

    response = await async_client.post("/auth/forgot-password", json=payload)

    assert response.status_code == status.HTTP_200_OK
    assert (
        response.json()["detail"]
        == "If an account with that email exists and is verified, a password reset link has been sent."
    )
    mock_forgot_pw.assert_awaited_once()
    call_args, call_kwargs = mock_forgot_pw.call_args
    assert call_args[0].email == payload["email"]
    assert isinstance(call_args[1], AsyncMock)


@pytest.mark.asyncio
@patch("app.auth.routes.reset_password", new_callable=AsyncMock)
async def test_reset_password_success(
    mock_reset_pw: AsyncMock, async_client: AsyncClient, override_get_db: None
) -> None:
    """Test successfully resetting password with a valid token"""
    mock_reset_pw.return_value = MessageResponse(
        detail="Your password has been successfully reset."
    )
    payload = ResetPasswordRequest(
        token="valid-reset-token", new_password="NewStrongPassword@1"
    ).model_dump()

    response = await async_client.post("/auth/reset-password", json=payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["detail"] == "Your password has been successfully reset."
    mock_reset_pw.assert_awaited_once()
    call_args, call_kwargs = mock_reset_pw.call_args
    assert call_args[0].token == payload["token"]
    assert call_args[0].new_password == payload["new_password"]
    assert isinstance(call_args[1], AsyncMock)


@pytest.mark.asyncio
@patch("app.auth.routes.reset_password", new_callable=AsyncMock)
async def test_reset_password_invalid_token(
    mock_reset_pw: AsyncMock, async_client: AsyncClient, override_get_db: None
) -> None:
    """Test resetting password with an invalid token"""
    mock_reset_pw.side_effect = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token."
    )
    payload = ResetPasswordRequest(
        token="invalid-reset-token", new_password="NewStrongPassword@1"
    ).model_dump()

    response = await async_client.post("/auth/reset-password", json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Invalid token."
    mock_reset_pw.assert_awaited_once()


# ===========================
# --- Email Update Tests ---
# ===========================
@pytest.mark.asyncio
@patch("app.auth.routes.request_email_update", new_callable=AsyncMock)
async def test_request_email_update_success(
    mock_req_update: AsyncMock,
    mock_current_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test successfully requesting an email update"""
    new_email = "new.email@example.com"
    mock_req_update.return_value = MessageResponse(
        detail=f"A verification link has been sent to {new_email}. Please check that inbox to confirm the change."
    )
    payload = UpdateEmailRequest(new_email=new_email).model_dump()
    # Need auth header because route depends on get_current_user
    headers = {"Authorization": "Bearer dummy-token-for-update-request"}

    response = await async_client.post("/auth/update-email", json=payload, headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert (
        response.json()["detail"]
        == f"A verification link has been sent to {new_email}. Please check that inbox to confirm the change."
    )
    mock_req_update.assert_awaited_once()
    call_args, call_kwargs = mock_req_update.call_args
    assert call_args[0].new_email == new_email
    assert call_args[1].id == mock_current_client_user.id
    assert isinstance(call_args[2], AsyncMock)


@pytest.mark.asyncio
@patch("app.auth.routes.request_email_update", new_callable=AsyncMock)
async def test_request_email_update_email_taken(
    mock_req_update: AsyncMock,
    mock_current_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test requesting email update when new email is already taken"""
    new_email = "taken.email@example.com"
    mock_req_update.side_effect = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="This email address is already in use by another verified account.",
    )
    payload = UpdateEmailRequest(new_email=new_email).model_dump()
    headers = {"Authorization": "Bearer dummy-token-for-update-request"}

    response = await async_client.post("/auth/update-email", json=payload, headers=headers)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        response.json()["detail"]
        == "This email address is already in use by another verified account."
    )
    mock_req_update.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.auth.routes.verify_new_email", new_callable=AsyncMock)
async def test_verify_new_email_success(
    mock_verify_new: AsyncMock, async_client: AsyncClient, override_get_db: None
) -> None:
    """Test successfully verifying a new email address"""
    mock_verify_new.return_value = MessageResponse(
        detail="Your email address has been successfully updated."
    )
    token = "valid-new-email-token"

    response = await async_client.get(f"/auth/verify-new-email?token={token}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["detail"] == "Your email address has been successfully updated."
    mock_verify_new.assert_awaited_once()
    call_args, call_kwargs = mock_verify_new.call_args
    assert call_args[0] == token
    assert isinstance(call_args[1], AsyncMock)


@pytest.mark.asyncio
@patch("app.auth.routes.verify_new_email", new_callable=AsyncMock)
async def test_verify_new_email_invalid_token(
    mock_verify_new: AsyncMock, async_client: AsyncClient, override_get_db: None
) -> None:
    """Test verifying new email with an invalid token"""
    mock_verify_new.side_effect = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token."
    )
    token = "invalid-new-email-token"

    response = await async_client.get(f"/auth/verify-new-email?token={token}")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Invalid token."
    mock_verify_new.assert_awaited_once()
