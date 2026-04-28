from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from centurion_bot.config import settings
from centurion_bot.db.base import Base

_url = settings.database_url

if _url.startswith("sqlite"):
    Path("data").mkdir(exist_ok=True)

engine = create_async_engine(_url, echo=False)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session  # type: ignore[misc]
