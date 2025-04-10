# tests/test_db_connection.py
import pytest
from sqlalchemy import text

@pytest.mark.asyncio
async def test_db_connection(db_session):
    async with db_session() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1

