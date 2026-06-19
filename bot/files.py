import logging
from io import BytesIO

import httpx

from telegram import InputFile

from config import settings

logger = logging.getLogger(__name__)


async def upload_file_to_group(file_bytes: bytes, filename: str) -> tuple[str, str]:
    from bot.router import application

    msg = await application.bot.send_document(
        chat_id=settings.telegram_group_id,
        document=InputFile(BytesIO(file_bytes), filename=filename),
    )
    doc = msg.document
    return doc.file_id, doc.file_name or filename


async def migrate_cloudinary_file(url: str, name_hint: str | None = None) -> tuple[str, str] | None:
    if not url or "cloudinary" not in url:
        return None
    filename = name_hint or url.rsplit("/", 1)[-1].split("?")[0]
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            resp.raise_for_status()
        return await upload_file_to_group(resp.content, filename)
    except Exception as e:
        logger.error("Failed to migrate Cloudinary file: url=%s error=%s", url, e)
        return None
