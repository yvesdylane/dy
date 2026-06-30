import logging
import os
from io import BytesIO

import httpx

from telegram import InputFile

from previouse.config import settings

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 50 * 1024 * 1024
ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf",
    ".doc", ".docx", ".xls", ".xlsx",
    ".txt", ".csv", ".md",
}


def validate_file(file_bytes: bytes, filename: str) -> tuple[bool, str]:
    if len(file_bytes) > MAX_FILE_SIZE:
        return False, f"File too large ({len(file_bytes) / 1024 / 1024:.1f}MB max {MAX_FILE_SIZE / 1024 / 1024:.0f}MB)"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File extension '{ext}' not allowed"
    return True, ""


async def upload_file_to_group(file_bytes: bytes, filename: str) -> tuple[str, str]:
    valid, err = validate_file(file_bytes, filename)
    if not valid:
        raise ValueError(err)

    from previouse.bot.router import application

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
