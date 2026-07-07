import logging
import os
from io import BytesIO

from telegram import InputFile

from config import settings

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


async def upload_file_to_group(bot, file_bytes: bytes, filename: str) -> tuple[str, str]:
    valid, err = validate_file(file_bytes, filename)
    if not valid:
        raise ValueError(err)

    msg = await bot.send_document(
        chat_id=settings.telegram_group_id,
        document=InputFile(BytesIO(file_bytes), filename=filename),
    )
    doc = msg.document
    return doc.file_id, doc.file_name or filename
