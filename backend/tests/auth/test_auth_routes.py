# # tests/auth/test_auth_routes.py

# """
# Unit tests for authentication routes.
# Covers: /auth/signup, /auth/login/json, /auth/login/oauth
# """

# import pytest
# from httpx import AsyncClient
# from app.database.enums import UserRole


# @pytest.mark.asyncio
# async def test_signup_success(async_client: AsyncClient):
#     payload = {
#         "email": "testuser@example.com",
#         "phone_number": "08012345678",
#         "password": "testpass123",
#         "first_name": "Test",
#         "last_name": "User",
#         "role": "CLIENT"
#     }
#     response = await async_client.post("/auth/signup", json=payload)
#     assert response.status_code == 200
#     data = response.json()
#     assert "access_token" in data
#     assert data["user"]["email"] == payload["email"]
#     assert data["user"]["role"] == payload["role"]


# @pytest.mark.asyncio
# async def test_signup_duplicate_email(async_client: AsyncClient):
#     payload = {
#         "email": "testdupe@example.com",
#         "phone_number": "08087654321",
#         "password": "testpass321",
#         "first_name": "Dupe",
#         "last_name": "User",
#         "role": "CLIENT"
#     }
#     # First signup should succeed
#     await async_client.post("/auth/signup", json=payload)
#     # Second signup should fail
#     response = await async_client.post("/auth/signup", json=payload)
#     assert response.status_code == 400
#     assert response.json()["detail"] == "Email already registered"


# @pytest.mark.asyncio
# async def test_login_json_success(async_client: AsyncClient):
#     signup_payload = {
#         "email": "loginuser@example.com",
#         "phone_number": "08111111111",
#         "password": "securepass",
#         "first_name": "Login",
#         "last_name": "User",
#         "role": "WORKER"
#     }
#     await async_client.post("/auth/signup", json=signup_payload)

#     login_payload = {
#         "email": signup_payload["email"],
#         "password": signup_payload["password"]
#     }
#     response = await async_client.post("/auth/login/json", json=login_payload)
#     assert response.status_code == 200
#     data = response.json()
#     assert "access_token" in data
#     assert data["user"]["email"] == signup_payload["email"]
#     assert data["user"]["role"] == signup_payload["role"]


# @pytest.mark.asyncio
# async def test_login_json_invalid_password(async_client: AsyncClient):
#     signup_payload = {
#         "email": "wrongpass@example.com",
#         "phone_number": "08122223333",
#         "password": "realpass",
#         "first_name": "Wrong",
#         "last_name": "Pass",
#         "role": "WORKER"
#     }
#     await async_client.post("/auth/signup", json=signup_payload)

#     bad_login = {
#         "email": signup_payload["email"],
#         "password": "incorrect"
#     }
#     response = await async_client.post("/auth/login/json", json=bad_login)
#     assert response.status_code == 401
#     assert response.json()["detail"] == "Invalid credentials"
