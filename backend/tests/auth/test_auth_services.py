# tests/auth/test_auth_services.py
import pytest

def test_client_token(client_token, client_user):
    assert client_token is not None
    assert isinstance(client_token, str)

@pytest.mark.asyncio
async def test_client_user(client_user):
    assert client_user.email.startswith("client_")
    assert client_user.role == "CLIENT"