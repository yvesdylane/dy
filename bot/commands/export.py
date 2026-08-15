import logging
from datetime import date
from io import BytesIO

from telegram import Update
from telegram.ext import CommandHandler

from bot.commands.admin import _is_staff
from controllers.exportController import fetch_interns
from db.database import get_sync_db
from utils.excel_export import build_excel

logger = logging.getLogger(__name__)


async def export_interns(update: Update, _context):
    if not await _is_staff(update):
        return

    try:
        with get_sync_db() as session:
            rows = fetch_interns(session)
    except Exception as e:
        logger.error("Intern export failed: %s", e, exc_info=True)
        await update.message.reply_text(f"\u274c Export failed: {e}")
        return

    if not rows:
        await update.message.reply_text("No interns found.")
        return

    filename = f"interns_{date.today().isoformat()}.xlsx"
    await update.message.reply_document(
        document=BytesIO(build_excel(rows)),
        filename=filename,
        caption=f"Intern list ({len(rows)} users)",
    )


export_handlers = [
    CommandHandler("export_interns", export_interns),
]
