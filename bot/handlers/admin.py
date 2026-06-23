import logging
import os
import tempfile
from urllib.parse import urlparse

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from bot.handlers.common import get_user, logger
from config import settings

SYNC_FILE = 0


async def cancel(update: Update, _context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


async def db_backup(update: Update, _context):
    from models.models import Role

    telegram_id = str(update.effective_user.id)
    user = await get_user(telegram_id)
    if not user or user.role != Role.admin:
        await update.message.reply_text("Only admins can use this command.")
        return

    parsed = urlparse(settings.database_url)
    db_path = parsed.path.lstrip("/")
    if not os.path.exists(db_path):
        await update.message.reply_text("Database file not found.")
        return

    await update.message.reply_document(
        document=open(db_path, "rb"),
        filename="dy_backup.db",
        caption="📦 Database backup",
    )


def _validate_db_schema(db_path: str) -> tuple[bool, str]:
    import sqlite3

    EXPECTED = {
        "users", "attendances", "intern_attendances", "tasks",
        "task_submissions", "infos", "notes", "creation_codes",
    }
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        missing = EXPECTED - tables
        if missing:
            return False, f"Missing tables: {', '.join(sorted(missing))}"
        return True, "Schema OK"
    except Exception as e:
        return False, str(e)


async def sync_start(update: Update, _context):
    from models.models import Role

    user = await get_user(str(update.effective_user.id))
    if not user or user.role != Role.admin:
        await update.message.reply_text("Only admins can use this command.")
        return ConversationHandler.END

    await update.message.reply_text("Upload the *.db* file to sync:")
    return SYNC_FILE


async def sync_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)
    document = update.message.document
    if not document or not document.file_name.lower().endswith(".db"):
        await update.message.reply_text("Please send a .db file.")
        return SYNC_FILE

    msg = await update.message.reply_text("Downloading database file...")

    file = await context.bot.get_file(document.file_id)
    tmp_path = os.path.join(tempfile.gettempdir(), f"sync_{telegram_id}_{document.file_name}")
    await file.download_to_drive(tmp_path)

    valid, err = _validate_db_schema(tmp_path)
    if not valid:
        os.remove(tmp_path)
        await msg.edit_text(f"❌ Invalid database format: {err}")
        return ConversationHandler.END

    await msg.edit_text("Syncing data...")
    try:
        from db.sync import sync_database
        result = await sync_database(tmp_path)
        await msg.edit_text(f"✅ Sync complete!\n{result}")
    except Exception as e:
        await msg.edit_text(f"❌ Sync failed: {e}")
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


async def handle_attendance_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from datetime import date, datetime

    from sqlalchemy import select

    from db.database import async_session
    from models.models import Attendance, AttendanceCode, Group, InternAttendance, User

    code_str = update.message.text.lstrip("/").upper()
    telegram_id = str(update.effective_user.id)

    async with async_session() as session:
        async with session.begin():
            now = datetime.utcnow()
            row = await session.execute(
                select(AttendanceCode).where(AttendanceCode.code == code_str)
            )
            row = row.scalar_one_or_none()

            if not row:
                await update.message.reply_text("Invalid or expired code.")
                return

            if row.expires_at < now:
                await session.delete(row)
                await update.message.reply_text("Code expired.")
                return

            user = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = user.scalar_one_or_none()

            if not user:
                await update.message.reply_text("You need to create an account first. Use /start.")
                return

            weekday = date.today().weekday()
            if weekday == 6:
                await update.message.reply_text("No attendance on Sundays.")
                return

            today_group = Group.A if weekday in (0, 2, 4) else Group.B

            if user.group != today_group:
                await update.message.reply_text(
                    f"Today is Group {today_group.value}, you are Group {user.group.value}."
                )
                return

            att = await session.execute(
                select(Attendance).where(
                    Attendance.date == date.today(),
                    Attendance.group == today_group,
                )
            )
            att = att.scalar_one_or_none()
            if not att:
                att = Attendance(date=date.today(), group=today_group)
                session.add(att)
                await session.flush()

            entry = await session.execute(
                select(InternAttendance).where(
                    InternAttendance.attendance_id == att.id,
                    InternAttendance.user_id == user.id,
                )
            )
            entry = entry.scalar_one_or_none()

            if not entry:
                entry = InternAttendance(
                    attendance_id=att.id,
                    user_id=user.id,
                    enter_at=now,
                )
                session.add(entry)
                msg = f"✅ Entry marked at {now.strftime('%H:%M')}"
            elif entry.enter_at and not entry.left_at:
                entry.left_at = now
                msg = f"✅ Exit marked at {now.strftime('%H:%M')}"
            else:
                await session.delete(row)
                await update.message.reply_text("Attendance already completed for today.")
                return

            await session.delete(row)
            await update.message.reply_text(msg)


async def cleaning_cmd(update: Update, context):
    from datetime import date

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from db.database import async_session
    from models.models import CleaningDuty, CleaningGroup, CleaningGroupMember

    user = await get_user(str(update.effective_user.id))
    if not user:
        await update.message.reply_text("User not found.")
        return

    async with async_session() as session:
        today = date.today()
        duty = (await session.execute(
            select(CleaningDuty)
            .options(
                selectinload(CleaningDuty.group).selectinload(CleaningGroup.members).selectinload(CleaningGroupMember.user),
                selectinload(CleaningDuty.completions),
            )
            .where(CleaningDuty.date == today)
        )).scalar_one_or_none()

    if not duty:
        await update.message.reply_text("No cleaning duty assigned today.")
        return

    lines = [f"🧹 *Today's Cleaning Duty*", f"Group: *{duty.group.name}*", ""]
    completed_ids = {c.user_id for c in duty.completions} if duty.completions else set()
    for m in duty.group.members:
        status = "✅ Done" if m.user_id in completed_ids else "⬜ Pending"
        marker = " ⬅️ You" if m.user_id == user.id else ""
        lines.append(f"• {m.user.name} {m.user.surname} — {status}{marker}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def qr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from datetime import date

    import base64
    from io import BytesIO

    import qrcode

    from sqlalchemy import select

    from config import settings
    from db.database import async_session
    from models.models import Role, User
    from web.security import create_qr_payload

    telegram_id = str(update.effective_user.id)
    user = await get_user(telegram_id)
    if not user or user.role not in (Role.admin, Role.instructor):
        await update.message.reply_text("Only admins and instructors can use this command.")
        return

    d, s = create_qr_payload(telegram_id, settings.telegram_token)
    bot_username = context.bot.username
    combined = base64.urlsafe_b64encode(f"{d}|{s}".encode()).decode().rstrip("=")
    qr_url = f"https://t.me/{bot_username}/dyd?startapp=M{combined}"

    qr = qrcode.make(qr_url)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)

    caption = f"📌 Attendance QR Code (valid for 1 hour)\nDate: {date.today()}\nGenerated by: {user.name} {user.surname}"

    await update.message.reply_photo(photo=buf, caption=caption)

    async with async_session() as session:
        staff = await session.execute(
            select(User).where(User.role.in_([Role.admin, Role.instructor]))
        )
        staff = staff.scalars().all()

    bot = context.bot
    for s in staff:
        if s.telegram_id == telegram_id:
            continue
        try:
            buf.seek(0)
            await bot.send_photo(chat_id=s.telegram_id, photo=buf, caption=caption)
        except Exception:
            logger.warning("Failed to send QR to user %s", s.telegram_id)


admin_handlers = [
    sync_conv,
    CommandHandler("db", db_backup),
    CommandHandler("sync", sync_start),
    CommandHandler("cleaning", cleaning_cmd),
    CommandHandler("qr", qr_command),
    MessageHandler(filters.Regex(r"^/[A-Z0-9]{5}$"), handle_attendance_code),
]
