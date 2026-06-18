import logging
from datetime import date
from urllib.parse import urlparse

from sqlalchemy import select
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


async def seed_admin(session: AsyncSession):
    from models.models import Department, Gender, Role, User

    result = await session.execute(
        select(User).where(User.telegram_id == "1235750724")
    )
    if result.scalar_one_or_none():
        return

    session.add(
        User(
            name="Yves",
            surname="Dylane",
            phone="+2375150173",
            telegram_id="1235750724",
            gender=Gender.male,
            role=Role.admin,
            department=Department.SWE,
            school="Default",
            dob=date(2003, 5, 24),
        )
    )
    logger.info("Default admin user created")


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
            from sqlalchemy import text as sa_text
            try:
                await conn.execute(sa_text("ALTER TABLE infos ADD COLUMN file_url VARCHAR(500)"))
            except Exception:
                pass
            try:
                await conn.execute(sa_text("ALTER TABLE users ADD COLUMN image VARCHAR(500)"))
            except Exception:
                pass

        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            async with session.begin():
                await seed_admin(session)

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
