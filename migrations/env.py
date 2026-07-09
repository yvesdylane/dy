import logging
from logging.config import fileConfig

from sqlalchemy import create_engine, pool

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

normalized_url, connect_args = normalize_url(settings.database_url)
config.set_main_option("sqlalchemy.url", normalized_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramtype": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(normalized_url, poolclass=pool.NullPool, connect_args=connect_args)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
