import asyncio
import logging
from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from config import settings

# Import all models so Alembic can detect them
from db.database import Base, normalize_url
from models import *  # noqa: F401, F403

logger = logging.getLogger(__name__)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

raw_url = settings.database_url
_is_libsql = "libsql" in raw_url

normalized_url, connect_args = normalize_url(raw_url)
config.set_main_option("sqlalchemy.url", normalized_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_sync() -> None:
    """Sync path for libsql (Turso) which lacks a fully working async driver."""
    connectable = create_engine(normalized_url, poolclass=pool.NullPool, connect_args=connect_args)
    with connectable.connect() as connection:
        do_run_migrations(connection)
    connectable.dispose()


async def run_async_migrations() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    connectable = async_engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    if _is_libsql:
        logger.info("Using sync engine for libsql (Turso) migration")
        run_migrations_sync()
    else:
        asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
