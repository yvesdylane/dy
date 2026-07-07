import io
import logging
import shutil
from datetime import date
from pathlib import Path
from uuid import uuid4

from telegram import InputFile

from config import settings

logger = logging.getLogger(__name__)


async def backup_db():
    from cronjobs.scheduler import get_bot

    bot = get_bot()
    if not bot:
        logger.warning("Bot not available, skipping DB backup")
        return

    db_path = Path("dy.db")
    if not db_path.exists():
        logger.warning("dy.db not found, skipping backup")
        return

    backup_path = Path(f"/tmp/dy_backup_{uuid4().hex[:8]}.db")
    try:
        shutil.copy2(str(db_path), str(backup_path))
        with open(backup_path, "rb") as f:
            buf = io.BytesIO(f.read())
        await bot.send_document(
            chat_id=settings.telegram_group_id,
            document=InputFile(buf, filename=f"dy_backup_{date.today().isoformat()}.db"),
            caption=f"📦 DB Backup — {date.today().isoformat()}",
        )
        logger.info("DB backup sent to group")
    except Exception as e:
        logger.error("DB backup failed: %s", e)
    finally:
        if backup_path.exists():
            backup_path.unlink()
