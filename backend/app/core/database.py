from functools import lru_cache
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import get_settings


@lru_cache()
def get_engine() -> AsyncEngine:
    settings = get_settings()
    kwargs = {"echo": settings.DEBUG, "future": True}
    if not settings.DATABASE_URL.startswith("sqlite"):
        kwargs["pool_pre_ping"] = True
    return create_async_engine(settings.DATABASE_URL, **kwargs)


@lru_cache()
def get_session_maker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


def AsyncSessionLocal() -> AsyncSession:
    return get_session_maker()()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
