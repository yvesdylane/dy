import logging
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


engine = None
async_session = None


def _engine_kwargs():
    parsed = urlparse(settings.database_url)
    if parsed.scheme.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {}


async def init_db():
    global engine, async_session

    import models.models  # noqa: F401

    try:
        engine = create_async_engine(
            settings.database_url,
            **_engine_kwargs(),
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        logger.info("Database ready")
    except Exception as e:
        logger.error("Database connection failed: %s", e)
        raise


async def close_db():
    global engine
    if engine:
        await engine.dispose()
        logger.info("Database engine disposed")


async def get_db():
    if async_session is None:
        raise RuntimeError("Database not initialized")
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
