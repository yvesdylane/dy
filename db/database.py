import asyncio
import logging
import subprocess
import sys
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


sync_engine = None
SyncSession = None
_is_turso = False


def normalize_url(url: str) -> tuple[str, dict]:
    connect_args = {}
    if url.startswith("libsql://"):
        url = url.replace("libsql://", "sqlite+libsql://", 1)
        url += "?secure=true" if "?" not in url else "&secure=true"
        connect_args["auth_token"] = settings.turso_auth_token
    elif url.startswith("sqlite") and "aiosqlite" in url:
        connect_args["check_same_thread"] = False
    return url, connect_args


def run_migrations():
    alembic_ini = Path(__file__).parent.parent / "alembic.ini"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=alembic_ini.parent,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error("Migration failed:\n%s\n%s", result.stdout, result.stderr)
        raise RuntimeError(f"Alembic migration failed: {result.stderr}")
    logger.info("Migrations up to date")


def init_db():
    global sync_engine, SyncSession, _is_turso

    raw_url = settings.database_url
    _is_turso = "libsql" in raw_url

    url, connect_args = normalize_url(raw_url)

    kwargs: dict = {
        "pool_pre_ping": True,
        "connect_args": connect_args,
    }

    if _is_turso:
        kwargs["poolclass"] = NullPool

    sync_engine = create_engine(url, **kwargs)
    SyncSession = sessionmaker(bind=sync_engine)

    run_migrations()

    logger.info("Database ready (url: %s)", raw_url)


def close_db():
    global sync_engine
    if sync_engine:
        sync_engine.dispose()
        sync_engine = None
        logger.info("Database engine disposed")


async def get_db() -> AsyncGenerator[Session, None]:
    """Async generator that wraps a sync session via run_in_executor."""
    if SyncSession is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    loop = asyncio.get_running_loop()
    session = await loop.run_in_executor(None, SyncSession)
    try:
        yield session
        await loop.run_in_executor(None, session.commit)
    except Exception:
        await loop.run_in_executor(None, session.rollback)
        raise
    finally:
        await loop.run_in_executor(None, session.close)


def get_sync_db() -> Generator[Session, None, None]:
    """Sync version of get_db for non-async contexts."""
    if SyncSession is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    session = SyncSession()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def check_db() -> bool:
    if not sync_engine:
        return False
    try:
        loop = asyncio.get_running_loop()

        def _ping():
            with sync_engine.connect() as c:
                c.execute(text("SELECT 1"))

        await loop.run_in_executor(None, _ping)
        return True
    except Exception as e:
        logger.warning("DB check failed: %s", e)
        return False
