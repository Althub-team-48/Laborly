"""
tests/auth/test_auth_routes.py

Tests for authentication routes:
- /auth/signup
- /auth/login/json
- /auth/logout

Note:
- Google OAuth endpoints are excluded from these tests.
"""

import uuid
import pytest
from httpx import AsyncClient
from fastapi import status



@pytest.mark.asyncio
async def test_signup_success(async_client: AsyncClient):
    """Test successful signup with unique email and phone number."""
    unique_email = f"signup_{uuid.uuid4().hex[:8]}@test.com"
    unique_phone = f"0801{str(uuid.uuid4().int)[-7:]}"

    response = await async_client.post("/auth/signup", json={
        "email": unique_email,
        "phone_number": unique_phone,
        "password": "securepass123",
        "first_name": "Sign",
        "last_name": "Up",
        "role": "CLIENT"
    })

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == unique_email


@pytest.mark.asyncio
async def test_signup_duplicate_email(async_client: AsyncClient):
    """Test signup failure when using an email that already exists."""
    payload = {
        "email": "duplicate@example.com",
        "phone_number": "08000000000",
        "password": "password123",
        "first_name": "Test",
        "last_name": "User",
        "role": "CLIENT"
    }

    await async_client.post("/auth/signup", json=payload)
    response = await async_client.post("/auth/signup", json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Email already registered"


@pytest.mark.asyncio
async def test_login_json_success(async_client: AsyncClient):
    """Test successful login using JSON credentials."""
    unique_email = f"login_{uuid.uuid4().hex[:8]}@test.com"
    unique_phone = f"0802{str(uuid.uuid4().int)[-7:]}"

    signup_response = await async_client.post("/auth/signup", json={
        "email": unique_email,
        "phone_number": unique_phone,
        "password": "loginpass",
        "first_name": "Login",
        "last_name": "User",
        "role": "WORKER"
    })

    assert signup_response.status_code == status.HTTP_201_CREATED

    login_response = await async_client.post("/auth/login/json", json={
        "email": unique_email,
        "password": "loginpass"
    })

    assert login_response.status_code == status.HTTP_200_OK
    assert "access_token" in login_response.json()


@pytest.mark.asyncio
async def test_login_json_invalid_credentials(async_client: AsyncClient):
    """Test login failure with incorrect credentials."""
    response = await async_client.post("/auth/login/json", json={
        "email": "fakeuser@example.com",
        "password": "wrongpass"
    })

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_logout_success(async_client: AsyncClient, client_token: str):
    """Test successful logout with a valid JWT token."""
    headers = {"Authorization": f"Bearer {client_token}"}

    response = await async_client.post("/auth/logout", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["detail"] == "Logout successful"


@pytest.mark.asyncio
async def test_logout_invalid_token(async_client: AsyncClient):
    """Test logout failure when token is invalid or malformed."""
    headers = {"Authorization": "Bearer invalid.token.value"}

    response = await async_client.post("/auth/logout", headers=headers)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Invalid token"
