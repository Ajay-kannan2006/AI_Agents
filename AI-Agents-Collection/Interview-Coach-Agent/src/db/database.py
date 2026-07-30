import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config.settings import settings

db_dir = os.path.dirname(settings.DATABASE_URL.replace("sqlite+aiosqlite:///", ""))
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
