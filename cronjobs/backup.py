import asyncio
import io
import logging
from datetime import date
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from telegram import InputFile

from config import settings
from db.database import Base

logger = logging.getLogger(__name__)


def _dump_database(dest_path: str) -> None:
    """Copy all data from the configured database to a local SQLite file.

    Works for both local SQLite and remote Turso/libsql databases.
    """
    from db.database import sync_engine
    backup_engine = create_engine(f"sqlite:///{dest_path}")
    Base.metadata.create_all(backup_engine)

    with sync_engine.connect() as src_conn:
        with backup_engine.connect() as dst_conn:
            for table in Base.metadata.sorted_tables:
                rows = src_conn.execute(table.select()).fetchall()
                if not rows:
                    continue
                dst_conn.execute(table.insert(), [dict(r._mapping) for r in rows])
            dst_conn.commit()


async def backup_db():
    from db.database import sync_engine
    from cronjobs.scheduler import get_bot

    bot = get_bot()
    if not bot:
        logger.warning("Bot not available, skipping DB backup")
        return

    if sync_engine is None:
        logger.warning("Database not initialized, skipping backup")
        return

    logger.info("Starting DB backup...")
    backup_path = Path(f"/tmp/dy_backup_{uuid4().hex[:8]}.db")
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _dump_database, str(backup_path))
        logger.info("DB dump complete (%d bytes)", backup_path.stat().st_size)
        with open(backup_path, "rb") as f:
            buf = io.BytesIO(f.read())
        await bot.send_document(
            chat_id=settings.telegram_group_id,
            document=InputFile(buf, filename=f"dy_backup_{date.today().isoformat()}.db"),
            caption=f"DB Backup - {date.today().isoformat()}",
        )
        logger.info("DB backup sent to group (%d bytes)", buf.tell())
    except Exception as e:
        logger.error("DB backup failed: %s", e, exc_info=True)
    finally:
        if backup_path.exists():
            backup_path.unlink()
