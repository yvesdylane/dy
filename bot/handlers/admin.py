import logging
import os
import tempfile
from urllib.parse import urlparse

import re
from datetime import date
from io import BytesIO

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputFile, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

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


PICS_TARGET, PICS_FEES = range(2)


async def pics_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from models.models import Role

    user = await get_user(str(update.effective_user.id))
    if not user or user.role not in (Role.admin, Role.instructor):
        await update.message.reply_text("Only staff can use this command.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("👥 All Users", callback_data="pics_all")],
        [InlineKeyboardButton("👔 Staff only", callback_data="pics_staff")],
        [InlineKeyboardButton("🎓 Interns only", callback_data="pics_interns")],
        [InlineKeyboardButton("📋 Group A", callback_data="pics_group_A")],
        [InlineKeyboardButton("📋 Group B", callback_data="pics_group_B")],
    ]
    await update.message.reply_text(
        "Select which users to include:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return PICS_TARGET


async def pics_target_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    target = query.data
    context.user_data["pics_target"] = target

    if target == "pics_interns":
        await query.edit_message_text(
            "Enter the maximum remaining fees (total - paid) to include interns.\n"
            "Example: `5000` includes interns with ≤5000 remaining.\n"
            "Or send /skip for all interns.",
            parse_mode="Markdown",
        )
        return PICS_FEES

    await query.edit_message_text("Generating archive...")
    await _generate_pics(update, context)
    return ConversationHandler.END


async def pics_fees_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
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


async def _generate_pics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import shutil
    import uuid
    import zipfile
    from pathlib import Path

    from sqlalchemy import select

    from db.database import async_session
    from models.models import Group as GroupEnum, Role, User

    target = context.user_data.pop("pics_target", None)
    max_remaining = context.user_data.pop("pics_max_remaining", None)
    if not target:
        await update.effective_message.reply_text("Something went wrong. Use /pics to start over.")
        return

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

    async with async_session() as session:
        users = (await session.execute(stmt.order_by(User.role, User.name))).scalars().all()

    if not users:
        await update.effective_message.reply_text("No users found matching the criteria.")
        return

    tmp_root = Path(tempfile.gettempdir()) / f"user_images_{uuid.uuid4().hex[:12]}"
    staff_dir = tmp_root / "staff"
    interns_dir = tmp_root / "interns"
    staff_dir.mkdir(parents=True, exist_ok=True)
    interns_dir.mkdir(parents=True, exist_ok=True)

    from bot.router import application

    downloaded = 0
    skipped = 0
    used_names = set()

    for user in users:
        if not user.image or user.image.startswith("http"):
            skipped += 1
            continue

        folder = staff_dir if user.role in (Role.admin, Role.instructor) else interns_dir
        safe_name = re.sub(r'[^\w.-]', '_', user.name or "unknown")
        safe_surname = re.sub(r'[^\w.-]', '_', user.surname or "unknown")
        base = f"{safe_name}_{safe_surname}"
        filename = f"{base}.jpg"
        counter = 1
        while filename in used_names:
            filename = f"{base}_{counter}.jpg"
            counter += 1
        used_names.add(filename)

        try:
            file = await application.bot.get_file(user.image)
            file_bytes = await file.download_as_bytearray()
            (folder / filename).write_bytes(file_bytes)
            downloaded += 1
        except Exception as e:
            logger.warning("Failed to download image for user %s: %s", user.id, e)
            skipped += 1

    if downloaded == 0:
        shutil.rmtree(tmp_root, ignore_errors=True)
        await update.effective_message.reply_text("No valid profile pictures found to download.")
        return

    zip_path = Path(tempfile.gettempdir()) / f"user_images_{uuid.uuid4().hex[:8]}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fpath in sorted(tmp_root.rglob("*")):
            if fpath.is_file():
                zf.write(fpath, arcname=fpath.relative_to(tmp_root))

    today = date.today().isoformat()
    caption = f"📸 User profile pictures ({downloaded} images)\nDate: {today}"
    if skipped:
        caption += f"\nSkipped: {skipped} (no image or legacy URL)"

    try:
        await application.bot.send_document(
            chat_id=settings.telegram_group_id,
            document=InputFile(zip_path.open("rb"), filename=f"user_images_{today}.zip"),
            caption=caption,
        )
        await update.effective_message.reply_text(
            f"✅ Archived {downloaded} user images and sent to the group."
        )
    except Exception as e:
        logger.error("Failed to send zip to group: %s", e)
        await update.effective_message.reply_text(f"❌ Failed to send archive: {e}")

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
    sync_conv,
    pics_conv,
    CommandHandler("db", db_backup),
    CommandHandler("sync", sync_start),
    CommandHandler("cleaning", cleaning_cmd),
    CommandHandler("qr", qr_command),
    MessageHandler(filters.Regex(r"^/[A-Z0-9]{5}$"), handle_attendance_code),
]
