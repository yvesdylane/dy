import logging
import os
import re
import shutil
import sqlite3
import tempfile
import uuid
import zipfile
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputFile, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters

from bot.common import get_user_sync
from config import settings
from models.enums import Role

logger = logging.getLogger(__name__)

SYNC_FILE = 0
PICS_TARGET, PICS_FEES = range(2)

EXPECTED_TABLES = {
    "users", "attendances", "intern_attendances", "tasks",
    "task_submissions", "infos", "notes", "creation_codes",
}


async def _is_admin(update: Update) -> bool:
    user = get_user_sync(str(update.effective_user.id))
    if not user or user.role not in (Role.admin, Role.super_admin):
        await update.message.reply_text("Only admins can use this command.")
        return False
    return True


async def _is_staff(update: Update) -> bool:
    user = get_user_sync(str(update.effective_user.id))
    if not user or user.role not in (Role.admin, Role.super_admin, Role.instructor):
        await update.message.reply_text("Only staff can use this command.")
        return False
    return True


async def cancel(update: Update, _context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ── /db ─────────────────────────────────────────────────────────


async def db_backup(update: Update, _context):
    if not await _is_admin(update):
        return

    raw_url = settings.database_url
    if not raw_url.startswith("sqlite:///"):
        await update.message.reply_text("Database is not a local SQLite file.")
        return

    db_path = raw_url.replace("sqlite:///", "")
    if not os.path.exists(db_path):
        await update.message.reply_text("Database file not found.")
        return

    with open(db_path, "rb") as f:
        await update.message.reply_document(
            document=f,
            filename="dy_backup.db",
            caption="\U0001f4e6 Database backup",
        )


# ── /sync ───────────────────────────────────────────────────────


def _validate_db_schema(db_path: str) -> tuple[bool, str]:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        missing = EXPECTED_TABLES - tables
        if missing:
            return False, f"Missing tables: {', '.join(sorted(missing))}"
        return True, "Schema OK"
    except Exception as e:
        return False, str(e)


async def sync_start(update: Update, _context):
    if not await _is_admin(update):
        return ConversationHandler.END

    await update.message.reply_text("Upload the *.db* file to sync:")
    return SYNC_FILE


async def sync_receive(update: Update, context):
    telegram_id = str(update.effective_user.id)
    document = update.message.document
    if not document or not document.file_name.lower().endswith(".db"):
        await update.message.reply_text("Please send a .db file.")
        return SYNC_FILE

    msg = await update.message.reply_text("Downloading database file...")

    file = await context.bot.get_file(document.file_id)
    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", document.file_name or "sync.db")
    tmp_path = os.path.join(tempfile.gettempdir(), f"sync_{telegram_id}_{safe_name}")
    await file.download_to_drive(tmp_path)

    valid, err = _validate_db_schema(tmp_path)
    if not valid:
        os.remove(tmp_path)
        await msg.edit_text(f"\u274c Invalid database format: {err}")
        return ConversationHandler.END

    await msg.edit_text("Syncing data...")
    try:
        from db.sync import sync_from_backup
        result = sync_from_backup(tmp_path)
        await msg.edit_text(f"\u2705 Sync complete!\n{result}")
    except Exception as e:
        await msg.edit_text(f"\u274c Sync failed: {e}")
        logger.error("Sync error: %s", e, exc_info=True)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return ConversationHandler.END


sync_conv = ConversationHandler(
    entry_points=[CommandHandler("sync", sync_start)],
    states={
        SYNC_FILE: [MessageHandler(filters.Document.ALL, sync_receive)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)


# ── /pics ───────────────────────────────────────────────────────


async def _try_download_image(bot, file_id: str) -> bytes | None:
    try:
        file = await bot.get_file(file_id)
        return await file.download_as_bytearray()
    except Exception:
        pass
    if settings.old_bot_token:
        try:
            from db.sync import _try_download
            return _try_download(settings.old_bot_token, file_id)
        except Exception:
            pass
    return None


async def pics_start(update: Update, _context):
    if not await _is_staff(update):
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("\U0001f465 All Users", callback_data="pics_all")],
        [InlineKeyboardButton("\U0001f454 Staff only", callback_data="pics_staff")],
        [InlineKeyboardButton("\U0001f393 Interns only", callback_data="pics_interns")],
        [InlineKeyboardButton("\U0001f4cb Group A", callback_data="pics_group_A")],
        [InlineKeyboardButton("\U0001f4cb Group B", callback_data="pics_group_B")],
    ]
    await update.message.reply_text(
        "Select which users to include:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return PICS_TARGET


async def pics_target_chosen(update: Update, context):
    query = update.callback_query
    await query.answer()
    target = query.data
    context.user_data["pics_target"] = target

    if target == "pics_interns":
        await query.edit_message_text(
            "Enter the maximum remaining fees (total - paid) to include interns.\n"
            "Example: `5000` includes interns with \u22645000 remaining.\n"
            "Or send /skip for all interns.",
            parse_mode="Markdown",
        )
        return PICS_FEES

    await query.edit_message_text("Generating archive...")
    await _generate_pics(update, context)
    return ConversationHandler.END


async def pics_fees_input(update: Update, context):
    text = update.message.text.strip()
    if text != "/skip":
        try:
            context.user_data["pics_max_remaining"] = float(text)
        except ValueError:
            await update.message.reply_text("Invalid number. Enter a number or /skip:")
            return PICS_FEES

    await update.message.reply_text("Generating archive...")
    await _generate_pics(update, context)
    return ConversationHandler.END


async def _generate_pics(update: Update, context):
    from sqlalchemy import select

    from db.database import get_sync_db
    from models.enums import Group as GroupEnum
    from models.user import User

    target = context.user_data.pop("pics_target", None)
    max_remaining = context.user_data.pop("pics_max_remaining", None)
    if not target:
        await update.effective_message.reply_text("Something went wrong. Use /pics to start over.")
        return

    with get_sync_db() as session:
        stmt = select(User).where(User.image.isnot(None))
        if target == "pics_staff":
            stmt = stmt.where(User.role.in_([Role.admin, Role.instructor]))
        elif target == "pics_interns":
            stmt = stmt.where(User.role == Role.intern)
            if max_remaining is not None:
                stmt = stmt.where((User.total_fees - User.fees_paid) <= max_remaining)
        elif target == "pics_group_A":
            stmt = stmt.where(User.group == GroupEnum.A)
        elif target == "pics_group_B":
            stmt = stmt.where(User.group == GroupEnum.B)
        users = session.execute(stmt.order_by(User.role, User.name)).scalars().all()

    if not users:
        await update.effective_message.reply_text("No users found matching the criteria.")
        return

    tmp_root = Path(tempfile.gettempdir()) / f"user_images_{uuid.uuid4().hex[:12]}"
    staff_dir = tmp_root / "staff"
    interns_dir = tmp_root / "interns"
    staff_dir.mkdir(parents=True, exist_ok=True)
    interns_dir.mkdir(parents=True, exist_ok=True)

    bot = update.get_bot()
    downloaded = 0
    skipped = 0
    used_names = set()

    for user in users:
        if not user.image:
            skipped += 1
            continue

        folder = staff_dir if user.role in (Role.admin, Role.super_admin, Role.instructor) else interns_dir
        safe_name = re.sub(r'[^\w.-]', '_', user.name or "unknown")
        safe_surname = re.sub(r'[^\w.-]', '_', user.surname or "unknown")
        base = f"{safe_name}_{safe_surname}"
        filename = f"{base}.jpg"
        counter = 1
        while filename in used_names:
            filename = f"{base}_{counter}.jpg"
            counter += 1
        used_names.add(filename)

        image_bytes = await _try_download_image(bot, user.image)
        if image_bytes is None:
            logger.warning("Failed to download image for user %s", user.id)
            skipped += 1
            continue

        (folder / filename).write_bytes(image_bytes)
        downloaded += 1

    if downloaded == 0:
        shutil.rmtree(tmp_root, ignore_errors=True)
        await update.effective_message.reply_text("No valid profile pictures found to download.")
        return

    zip_path = Path(tempfile.gettempdir()) / f"user_images_{uuid.uuid4().hex[:8]}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fpath in sorted(tmp_root.rglob("*")):
            if fpath.is_file():
                zf.write(fpath, arcname=fpath.relative_to(tmp_root))

    from datetime import date

    today = date.today().isoformat()
    caption = f"\U0001f4f8 User profile pictures ({downloaded} images)\nDate: {today}"
    if skipped:
        caption += f"\nSkipped: {skipped} (no image or legacy URL)"

    try:
        await bot.send_document(
            chat_id=settings.telegram_group_id,
            document=InputFile(zip_path.open("rb"), filename=f"user_images_{today}.zip"),
            caption=caption,
        )
        await update.effective_message.reply_text(
            f"\u2705 Archived {downloaded} user images and sent to the group."
        )
    except Exception as e:
        logger.error("Failed to send zip to group: %s", e)
        await update.effective_message.reply_text(f"\u274c Failed to send archive: {e}")

    zip_path.unlink(missing_ok=True)
    shutil.rmtree(tmp_root, ignore_errors=True)


pics_conv = ConversationHandler(
    entry_points=[CommandHandler("pics", pics_start)],
    states={
        PICS_TARGET: [CallbackQueryHandler(pics_target_chosen, pattern="^pics_")],
        PICS_FEES: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, pics_fees_input),
            CommandHandler("skip", pics_fees_input),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)


admin_handlers = [
    CommandHandler("db", db_backup),
    sync_conv,
    pics_conv,
]
