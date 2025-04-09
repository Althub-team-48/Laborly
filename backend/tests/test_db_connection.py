# tests/test_db_connection.py
import pytest
from sqlalchemy.sql import text
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_db_connection(db_session: AsyncSession):
    async with db_session.begin():  # Explicitly start a transaction
        result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1  # Verify the result