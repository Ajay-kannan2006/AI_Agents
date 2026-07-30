from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db

async def get_async_db_session(db: AsyncSession = Depends(get_db)) -> AsyncSession:
    """Dependency helper for database session injection."""
    return db
