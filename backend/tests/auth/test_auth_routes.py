"""
tests/test_auth_routes.py

Unit tests for auth/routes.py with both success and failure scenarios
- Mocks service logic
- Uses Pytest fixtures for DRY code
- Uses ASGITransport to test FastAPI app with httpx
"""

import pytest
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport
from unittest.mock import AsyncMock, patch
from fastapi import status, HTTPException

from main import app

@pytest.fixture(scope="module")
def transport():
    return ASGITransport(app=app)


@pytest.mark.asyncio
@patch("app.auth.routes.signup_user", new_callable=AsyncMock)
async def test_signup_success(mock_signup, fake_auth_response, transport):
    mock_signup.return_value = fake_auth_response
    payload = {
        "email": "user@example.com",
        "phone_number": "1234567890",
        "password": "secret123",
        "first_name": "John",
        "last_name": "Doe",
        "role": "CLIENT"
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/auth/signup", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["access_token"] == fake_auth_response.access_token


@pytest.mark.asyncio
@patch("app.auth.routes.signup_user", new_callable=AsyncMock)
async def test_signup_duplicate_email(mock_signup, transport):
    mock_signup.side_effect = HTTPException(status_code=400, detail="Email already registered")
    payload = {
        "email": "existing@example.com",
        "phone_number": "1234567890",
        "password": "secret123",
        "first_name": "Jane",
        "last_name": "Doe",
        "role": "CLIENT"
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/auth/signup", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"


@pytest.mark.asyncio
@patch("app.auth.routes.login_user_json", new_callable=AsyncMock)
async def test_login_json_success(mock_login, fake_auth_response, transport):
    mock_login.return_value = fake_auth_response
    payload = {"email": "user@example.com", "password": "secret123"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/auth/login/json", json=payload)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["access_token"] == fake_auth_response.access_token


@pytest.mark.asyncio
@patch("app.auth.routes.login_user_json", new_callable=AsyncMock)
async def test_login_json_invalid_credentials(mock_login, transport):
    mock_login.side_effect = HTTPException(status_code=401, detail="Invalid credentials")
    payload = {"email": "user@example.com", "password": "wrongpass"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/auth/login/json", json=payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
@patch("app.auth.routes.login_user_oauth", new_callable=AsyncMock)
async def test_login_oauth_success(mock_oauth, fake_auth_response, transport):
    mock_oauth.return_value = fake_auth_response
    data = {"username": "user@example.com", "password": "secret123"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/auth/login/oauth", data=data)
    assert response.status_code == 200
    assert response.json()["access_token"] == fake_auth_response.access_token


@pytest.mark.asyncio
@patch("app.auth.routes.login_user_oauth", new_callable=AsyncMock)
async def test_login_oauth_invalid_credentials(mock_oauth, transport):
    mock_oauth.side_effect = HTTPException(status_code=401, detail="Invalid credentials")
    data = {"username": "user@example.com", "password": "wrongpass"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/auth/login/oauth", data=data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
@patch("app.auth.routes.handle_google_login", new_callable=AsyncMock)
async def test_google_login(mock_google_login, transport):
    mock_google_login.return_value = {"detail": "redirecting"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/auth/google/login")
    assert response.status_code == 200
    assert response.json()["detail"] == "redirecting"


@pytest.mark.asyncio
@patch("app.auth.routes.handle_google_callback", new_callable=AsyncMock)
async def test_google_callback(mock_callback, transport):
    mock_callback.return_value = {"detail": "callback processed"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/auth/google/callback")
    assert response.status_code == 200
    assert response.json()["detail"] == "callback processed"


@pytest.mark.asyncio
@patch("app.auth.routes.logout_user_token", return_value={"detail": "Logout successful"})
async def test_logout_user(mock_logout, transport):
    headers = {"Authorization": "Bearer dummy-token"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/auth/logout", headers=headers)
    assert response.status_code == 200
    assert response.json()["detail"] == "Logout successful"
