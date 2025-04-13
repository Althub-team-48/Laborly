# import pytest
# from httpx import AsyncClient
# from fastapi import status

# @pytest.mark.asyncio
# async def test_get_client_profile(async_client: AsyncClient, auth_headers: dict):
#     """Test the get client profile endpoint."""
#     response = await async_client.get("/client/get/profile", headers=auth_headers)
    
#     assert response.status_code == status.HTTP_200_OK
#     data = response.json()
#     assert "id" in data
#     assert "email" in data
#     assert "phone_number" in data