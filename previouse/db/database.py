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

from previouse.config import settings

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
    from previouse.models.models import Department, Gender, Role, User

    if not settings.super_admin_telegram_id:
        logger.warning("SUPER_ADMIN_TELEGRAM_ID not set — skipping super admin seed")
        return

    result = await session.execute(
        select(User).where(User.telegram_id == settings.super_admin_telegram_id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        if existing.role != Role.super_admin:
            existing.role = Role.super_admin
            logger.info("Promoted %s to super_admin", settings.super_admin_telegram_id)
        return

    try:
        dept = Department(settings.super_admin_department)
    except ValueError:
        dept = Department.SWE

    session.add(
        User(
            name=settings.super_admin_name,
            surname=settings.super_admin_surname,
            phone=settings.super_admin_phone or f"pending_{settings.super_admin_telegram_id}",
            telegram_id=settings.super_admin_telegram_id,
            gender=Gender.male,
            role=Role.super_admin,
            department=dept,
            school="Default",
            dob=date(2000, 1, 1),
        )
    )
    logger.info("Super admin user created from env config")


async def init_db():
    global engine, async_session

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
            try:
                await conn.execute(sa_text("ALTER TABLE tasks ADD COLUMN file_id VARCHAR(200)"))
            except Exception:
                pass
            try:
                await conn.execute(sa_text("ALTER TABLE tasks ADD COLUMN file_name VARCHAR(200)"))
            except Exception:
                pass
            try:
                await conn.execute(sa_text("ALTER TABLE task_submissions ADD COLUMN file_id VARCHAR(200)"))
            except Exception:
                pass
            try:
                await conn.execute(sa_text("ALTER TABLE task_submissions ADD COLUMN file_name VARCHAR(200)"))
            except Exception:
                pass
            try:
                await conn.execute(sa_text("ALTER TABLE notes ADD COLUMN file_id VARCHAR(200)"))
            except Exception:
                pass
            try:
                await conn.execute(sa_text("ALTER TABLE notes ADD COLUMN file_name VARCHAR(200)"))
            except Exception:
                pass
            try:
                await conn.execute(sa_text("ALTER TABLE infos ADD COLUMN file_id VARCHAR(200)"))
            except Exception:
                pass
            try:
                await conn.execute(sa_text("ALTER TABLE infos ADD COLUMN file_name VARCHAR(200)"))
            except Exception:
                pass
            try:
                await conn.execute(sa_text("ALTER TABLE intern_attendances ADD COLUMN status VARCHAR(20)"))
            except Exception:
                pass
            try:
                await conn.execute(sa_text("ALTER TABLE task_submissions ADD COLUMN submitted_url VARCHAR(1000)"))
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
