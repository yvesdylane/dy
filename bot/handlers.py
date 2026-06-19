import logging
import os
import tempfile
from urllib.parse import urlparse

from sqlalchemy import func, select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, WebAppInfo
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from config import settings

logger = logging.getLogger(__name__)

HELP_INFO_TEXT = "Select an option below to view information:"


async def get_user(telegram_id: str):
    from db.database import async_session
    from models.models import User

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()


def format_user_info(user) -> str:
    lines = [
        f"*Name:* {user.name} {user.surname}",
        f"*Phone:* {user.phone}",
        f"*Telegram ID:* `{user.telegram_id}`",
        f"*Gender:* {user.gender.value}",
        f"*Role:* {user.role.value}",
        f"*Department:* {user.department.value}",
        f"*School:* {user.school}",
        f"*DOB:* {user.dob}",
    ]
    if user.group:
        lines.insert(5, f"*Group:* {user.group.value}")
    if user.role.value == "intern":
        lines.append(f"*Quarter:* {user.quarter or 'N/A'}")
        lines.append(f"*Fees Paid:* {user.fees_paid or 0}")
        lines.append(f"*Total Fees:* {user.total_fees or 40000}")
    return "\n".join(lines)


def reply_fn(update: Update):
    if update.callback_query:
        return update.callback_query.message.reply_text
    return update.message.reply_text


def reply_md_fn(update: Update):
    if update.callback_query:
        return update.callback_query.message.reply_markdown
    return update.message.reply_markdown


async def send_user_info(telegram_id: str, update: Update):
    user = await get_user(telegram_id)
    reply_text = reply_fn(update)
    reply_md = reply_md_fn(update)

    if not user:
        mini_app_url = f"{settings.mini_app_url.rstrip('/')}/app"
        url_with_id = f"{mini_app_url}?telegram_id={telegram_id}"
        button = InlineKeyboardButton("Create Account", web_app=WebAppInfo(url=url_with_id))
        keyboard = InlineKeyboardMarkup([[button]])
        await reply_text(
            "You don't have an account yet. Tap the button below to create one.",
            reply_markup=keyboard,
        )
        return

    text = format_user_info(user)
    text += "\n\nUse /helpInfo to explore more info commands."

    image_id = user.image
    if image_id and image_id.startswith("http"):
        from bot.files import migrate_cloudinary_file
        result = await migrate_cloudinary_file(image_id, f"profile_{telegram_id}.jpg")
        if result:
            fid, _ = result
            from db.database import async_session
            from models.models import User as UserModel
            async with async_session() as session:
                async with session.begin():
                    u = await session.get(UserModel, user.id)
                    if u:
                        u.image = fid
            image_id = fid

    if image_id:
        try:
            from bot.router import application
            file = await application.bot.get_file(image_id)
            photo_bytes = await file.download_as_bytearray()
            await update.effective_message.reply_photo(
                photo=photo_bytes,
                caption=text,
                parse_mode="Markdown",
            )
        except Exception:
            await reply_md(text)
    else:
        await reply_md(text)


async def send_user_overview(telegram_id: str, update: Update):
    from db.database import async_session
    from models.models import Department, Role, User

    reply = reply_md_fn(update)

    me = await get_user(telegram_id)
    if not me:
        await reply("You need an account first. Use /info to create one.")
        return

    async with async_session() as session:
        base = select(func.count(User.id))
        dept_filter = [] if me.role != Role.intern else [User.department == me.department]

        total = (await session.execute(base.where(*dept_filter))).scalar()
        intern_count = (
            await session.execute(base.where(User.role == Role.intern, *dept_filter))
        ).scalar()
        instructor_count = (
            await session.execute(base.where(User.role == Role.instructor, *dept_filter))
        ).scalar()

    scope = "your department" if me.role == Role.intern else "all departments"
    text = (
        f"*User Overview ({scope})*\n\n"
        f"Total users: {total}\n"
        f"Interns: {intern_count}\n"
        f"Instructors: {instructor_count}"
    )
    if me.role != Role.intern:
        text += f"\nAdmins: {total - intern_count - instructor_count}"

    await reply(text)


async def send_task_overview(telegram_id: str, update: Update):
    from datetime import datetime

    from db.database import async_session
    from models.models import Department, Role, Task

    reply = reply_md_fn(update)

    me = await get_user(telegram_id)
    if not me:
        await reply("You need an account first.")
        return

    now = datetime.utcnow()
    async with async_session() as session:
        q = select(Task).where(Task.submission_deadline >= now)
        if me.role == Role.intern:
            q = q.where(Task.department == me.department)
        q = q.order_by(Task.submission_deadline)
        tasks = (await session.execute(q)).scalars().all()

    if not tasks:
        await reply("No active tasks found.")
        return

    btns = [InlineKeyboardButton(t.name, callback_data=f"task_{t.id}") for t in tasks]
    keyboard = [btns[i:i+2] for i in range(0, len(btns), 2)]
    scope = f"department *{me.department.value}*" if me.role == Role.intern else "all departments"
    await reply(
        f"*Active tasks ({scope}):*",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def me(update: Update, _context):
    telegram_id = str(update.effective_user.id)
    logger.info("=== /me called by user id=%s ===", telegram_id)
    try:
        await send_user_info(telegram_id, update)
    except Exception as e:
        logger.error("Me command failed: %s", e)
        reply = reply_fn(update)
        await reply("An error occurred. Please try again later.")


async def announcements(update: Update, _context):
    telegram_id = str(update.effective_user.id)
    try:
        from sqlalchemy import select

        from db.database import async_session
        from models.models import Info

        async with async_session() as session:
            items = (await session.execute(
                select(Info).order_by(Info.created_at.desc())
            )).scalars().all()

        if not items:
            await update.effective_message.reply_text("No announcements yet.")
            return

        btns = [InlineKeyboardButton(item.title[:40], callback_data=f"info_{item.id}") for item in items]
        keyboard = [btns[i:i+2] for i in range(0, len(btns), 2)]
        await update.effective_message.reply_text(
            "📢 *Announcements:*\nSelect one to view details.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    except Exception as e:
        logger.error("Info command failed: %s", e)
        reply = reply_fn(update)
        await reply("An error occurred.")


async def info_detail_callback(update: Update, _context):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import Info

    query = update.callback_query
    await query.answer()
    info_id = int(query.data.split("_")[1])

    async with async_session() as session:
        item = (await session.execute(select(Info).where(Info.id == info_id))).scalar_one_or_none()

    if not item:
        await query.message.reply_text("Announcement not found.")
        return

    text = f"*{item.title}*\n_{item.created_at.date()}_\n\n{item.content}"
    await query.message.reply_markdown(text)

    if item.file_id:
        try:
            await query.message.reply_document(
                document=item.file_id,
                filename=item.file_name or item.file_id,
                caption=f"📎 {item.title}",
            )
        except Exception as e:
            logger.error("Failed to send info file (file_id): error=%s", e)
    elif item.file_url:
        try:
            from bot.files import migrate_cloudinary_file
            result = await migrate_cloudinary_file(item.file_url, item.file_name)
            if result:
                fid, fname = result
                from db.database import async_session
                from models.models import Info
                async with async_session() as session:
                    async with session.begin():
                        obj = await session.get(Info, item.id)
                        if obj:
                            obj.file_id = fid
                            obj.file_name = fname
                await query.message.reply_document(
                    document=fid,
                    filename=fname,
                    caption=f"📎 {item.title}",
                )
        except Exception as e:
            logger.error("Failed to send info file: url=%s error=%s", item.file_url, e)


async def dashboard(update: Update, _context):
    telegram_id = str(update.effective_user.id)
    logger.info("=== /dashboard called by user id=%s ===", telegram_id)
    mini_app_url = f"{settings.mini_app_url.rstrip('/')}/app?telegram_id={telegram_id}"
    button = InlineKeyboardButton("Open Dashboard", web_app=WebAppInfo(url=mini_app_url))
    keyboard = InlineKeyboardMarkup([[button]])
    await update.message.reply_text(
        "Open your dashboard below:",
        reply_markup=keyboard,
    )


async def user_info(update: Update, _context):
    telegram_id = str(update.effective_user.id)
    try:
        await send_user_overview(telegram_id, update)
    except Exception as e:
        logger.error("User info failed: %s", e)
        reply = reply_fn(update)
        await reply("An error occurred.")


async def task_info(update: Update, _context):
    telegram_id = str(update.effective_user.id)
    try:
        await send_task_overview(telegram_id, update)
    except Exception as e:
        logger.error("Task info failed: %s", e)
        reply = reply_fn(update)
        await reply("An error occurred.")


async def task_detail_callback(update: Update, _context):
    from db.database import async_session
    from models.models import Task

    query = update.callback_query
    await query.answer()

    task_id = int(query.data.split("_")[1])
    async with async_session() as session:
        t = (await session.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()

    if not t:
        await query.message.reply_text("Task not found or has been removed.")
        return

    lines = [
        f"*{t.name}*",
        f"📝 *Description:* {t.description}",
        f"📅 *Deadline:* {t.submission_deadline.strftime('%Y-%m-%d %H:%M')}",
        f"🎯 *Total Mark:* {t.total_mark_on}",
    ]
    await query.message.reply_markdown("\n".join(lines))

    if t.file_id:
        try:
            await query.message.reply_document(
                document=t.file_id,
                filename=t.file_name or t.file_id,
                caption="📎 Supporting document",
            )
        except Exception as e:
            logger.error("Failed to send supporting doc (file_id): error=%s", e)
    elif t.supporting_doc:
        try:
            from bot.files import migrate_cloudinary_file
            result = await migrate_cloudinary_file(t.supporting_doc, t.file_name)
            if result:
                fid, fname = result
                from db.database import async_session
                from models.models import Task
                async with async_session() as session:
                    async with session.begin():
                        obj = await session.get(Task, t.id)
                        if obj:
                            obj.file_id = fid
                            obj.file_name = fname
                await query.message.reply_document(
                    document=fid,
                    filename=fname,
                    caption="📎 Supporting document",
                )
        except Exception as e:
            logger.error("Failed to send supporting doc: url=%s error=%s", t.supporting_doc, e)


async def help_info(update: Update, _context):
    keyboard = [
        [
            InlineKeyboardButton("👤 My Info", callback_data="info_user"),
            InlineKeyboardButton("📋 Tasks", callback_data="info_tasks"),
        ],
        [
            InlineKeyboardButton("✅ Attendance", callback_data="info_attendance"),
            InlineKeyboardButton("📝 Notes", callback_data="info_notes"),
        ],
        [InlineKeyboardButton("📢 Announcements", callback_data="info_announcements")],
    ]
    await update.message.reply_text(
        HELP_INFO_TEXT,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def info_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    telegram_id = str(query.from_user.id)

    handlers_map = {
        "info_user": send_user_overview,
        "info_tasks": send_task_overview,
        "info_attendance": lambda tid, u: reply_fn(u)("Attendance info coming soon."),
        "info_notes": lambda tid, u: notes_list(u, None),
        "info_announcements": lambda tid, u: announcements(u, None),
    }

    handler = handlers_map.get(query.data)
    if not handler:
        return

    try:
        await handler(telegram_id, update)
    except Exception as e:
        logger.error("Callback %s failed: %s", query.data, e)
        await query.message.reply_text("An error occurred.")


async def link_cmd(update: Update, _context):
    button = KeyboardButton("Share Contact", request_contact=True)
    markup = ReplyKeyboardMarkup([[button]], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "Share your phone number to link your Telegram account:",
        reply_markup=markup,
    )


async def handle_contact(update: Update, _context):
    contact = update.message.contact
    if not contact:
        return
    phone = contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone
    telegram_id = str(contact.user_id)

    from db.database import async_session
    from models.models import User

    async with async_session() as session:
        async with session.begin():
            user = (
                await session.execute(select(User).where(User.phone == phone))
            ).scalar_one_or_none()

            if not user:
                await update.message.reply_text(
                    "No account found with this phone number.",
                    reply_markup=ReplyKeyboardRemove(),
                )
                return

            if user.telegram_id and not user.telegram_id.startswith("pending_") and user.telegram_id != telegram_id:
                await update.message.reply_text(
                    "This phone is linked to a different account.",
                    reply_markup=ReplyKeyboardRemove(),
                )
                return

            if user.telegram_id == telegram_id:
                await update.message.reply_text(
                    "Already linked!",
                    reply_markup=ReplyKeyboardRemove(),
                )
                return

            user.telegram_id = telegram_id

    await update.message.reply_text(
        f"Linked! Welcome {user.name} {user.surname}.",
        reply_markup=ReplyKeyboardRemove(),
    )


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


TASK_NAME, TASK_DESC, TASK_DEPT, TASK_DEADLINE, TASK_MARK, TASK_DOC = range(6)
NOTE_TITLE, NOTE_CONTENT, NOTE_DEPT, NOTE_FILE = range(4)
SYNC_FILE = 0
SUBMIT_SELECT, SUBMIT_FILE = range(2)


async def cancel(update: Update, _context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


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


# ── /sync ──────────────────────────────────────────────────────────


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


# ── /submit ────────────────────────────────────────────────────────


async def submit_start(update: Update, _context):
    from datetime import datetime

    from db.database import async_session
    from models.models import Role, Task

    user = await get_user(str(update.effective_user.id))
    if not user:
        await update.message.reply_text("You need an account first.")
        return ConversationHandler.END

    now = datetime.utcnow()
    async with async_session() as session:
        tasks = (
            (await session.execute(
                select(Task).where(
                    Task.department == user.department,
                    Task.submission_deadline >= now,
                ).order_by(Task.submission_deadline)
            )).scalars().all()
        )

    if not tasks:
        await update.message.reply_text("No active tasks for your department.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(t.name, callback_data=f"submit_{t.id}")]
        for t in tasks
    ]
    await update.message.reply_text(
        "Select the task to submit:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return SUBMIT_SELECT


async def submit_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    task_id = int(query.data.split("_")[1])

    from db.database import async_session
    from models.models import Task

    async with async_session() as session:
        t = (await session.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()

    if not t:
        await query.message.reply_text("Task not found.")
        return ConversationHandler.END

    context.user_data["submit_task_id"] = task_id
    await query.message.reply_text(f"Upload your submission for *{t.name}*:")
    return SUBMIT_FILE


async def submit_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from db.database import async_session
    from models.models import Task, TaskSubmission

    user = await get_user(str(update.effective_user.id))
    task_id = context.user_data.get("submit_task_id")
    if not task_id or not user:
        await update.message.reply_text("Something went wrong. Start again with /submit.")
        return ConversationHandler.END

    if not update.message.document:
        await update.message.reply_text("Please upload a file.")
        return SUBMIT_FILE

    msg = await update.message.reply_text("Uploading submission...")

    file = await context.bot.get_file(update.message.document.file_id)
    file_bytes = await file.download_as_bytearray()

    from bot.files import upload_file_to_group
    file_id, file_name = await upload_file_to_group(bytes(file_bytes), update.message.document.file_name or "submission")

    async with async_session() as session:
        async with session.begin():
            session.add(TaskSubmission(
                task_id=task_id,
                user_id=user.id,
                submitted_file=file_id,
                file_id=file_id,
                file_name=file_name,
            ))

    context.user_data.pop("submit_task_id", None)
    await msg.edit_text("✅ Task submitted successfully!")
    return ConversationHandler.END


submit_conv = ConversationHandler(
    entry_points=[CommandHandler("submit", submit_start)],
    states={
        SUBMIT_SELECT: [CallbackQueryHandler(submit_select, pattern="^submit_")],
        SUBMIT_FILE: [MessageHandler(filters.Document.ALL, submit_file)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)


# ── /givetask ──────────────────────────────────────────────────────


async def give_task_start(update: Update, _context):
    from models.models import Role

    user = await get_user(str(update.effective_user.id))
    if not user or user.role not in (Role.admin, Role.instructor):
        await update.message.reply_text("Only admins and instructors can create tasks.")
        return ConversationHandler.END

    await update.message.reply_text("Send me the *task name*:")
    return TASK_NAME


async def give_task_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["task_name"] = update.message.text
    await update.message.reply_text("Send me the *description*:")
    return TASK_DESC


async def give_task_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["task_desc"] = update.message.text
    await update.message.reply_text(
        "Send the *department* (ISM / SWE / CGWD / EDM / CSNW / DBM / CNWS / NS)\n"
        "Or send `/skip` to use your own department."
    )
    return TASK_DEPT


async def skip_task_dept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(str(update.effective_user.id))
    context.user_data["task_dept"] = user.department
    await update.message.reply_text("Send the *duration* (e.g. `2 days`, `48 hours`, `1d`, `48h`):")
    return TASK_DEADLINE


async def give_task_dept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from models.models import Department

    try:
        context.user_data["task_dept"] = Department(update.message.text.strip().upper())
    except ValueError:
        await update.message.reply_text("Invalid department. Try: ISM / SWE / CGWD / EDM / CSNW / DBM / CNWS / NS")
        return TASK_DEPT

    await update.message.reply_text(
        "Send the *duration* (e.g. `2 days`, `48 hours`, `1d`, `48h`):"
    )
    return TASK_DEADLINE


async def give_task_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import re
    from datetime import datetime, timedelta

    text = update.message.text.strip().lower()
    match = re.match(r"(\d+)\s*(h|hr|hours|d|day|days)", text)
    if not match:
        await update.message.reply_text("Invalid format. Use e.g. `2 days`, `48 hours`, `1d`.")
        return TASK_DEADLINE

    amount = int(match.group(1))
    unit = match.group(2)
    if unit in ("h", "hr", "hours"):
        delta = timedelta(hours=amount)
    else:
        delta = timedelta(days=amount)

    context.user_data["task_deadline"] = datetime.utcnow() + delta

    await update.message.reply_text("Send the *total mark*:")
    return TASK_MARK


async def give_task_mark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["task_mark"] = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Invalid number. Send an integer.")
        return TASK_MARK

    await update.message.reply_text(
        "Upload the *supporting document* (or send `/skip` to skip):"
    )
    return TASK_DOC


async def skip_task_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from db.database import async_session
    from models.models import Task

    user = await get_user(str(update.effective_user.id))
    async with async_session() as session:
        async with session.begin():
            session.add(Task(
                name=context.user_data["task_name"],
                description=context.user_data["task_desc"],
                department=context.user_data["task_dept"],
                submission_deadline=context.user_data["task_deadline"],
                total_mark_on=context.user_data["task_mark"],
                supporting_doc=None,
                created_by=user.id,
            ))

    context.user_data.clear()
    await update.message.reply_text("✅ Task created successfully!")
    return ConversationHandler.END


async def give_task_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from db.database import async_session
    from models.models import Department, Task

    user = await get_user(str(update.effective_user.id))

    doc_url = None
    doc_id = None
    doc_name = None
    if update.message.document:
        file = await context.bot.get_file(update.message.document.file_id)
        file_bytes = await file.download_as_bytearray()
        from bot.files import upload_file_to_group
        doc_id, doc_name = await upload_file_to_group(bytes(file_bytes), update.message.document.file_name or "task_doc")
        doc_url = doc_id

    async with async_session() as session:
        async with session.begin():
            task = Task(
                name=context.user_data["task_name"],
                description=context.user_data["task_desc"],
                department=context.user_data["task_dept"],
                submission_deadline=context.user_data["task_deadline"],
                total_mark_on=context.user_data["task_mark"],
                supporting_doc=doc_url,
                file_id=doc_id,
                file_name=doc_name,
                created_by=user.id,
            )
            session.add(task)

    context.user_data.clear()
    await update.message.reply_text("✅ Task created successfully!")
    return ConversationHandler.END


give_task_conv = ConversationHandler(
    entry_points=[CommandHandler("givetask", give_task_start)],
    states={
        TASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, give_task_name)],
        TASK_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, give_task_desc)],
        TASK_DEPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, give_task_dept), CommandHandler("skip", skip_task_dept)],
        TASK_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, give_task_deadline)],
        TASK_MARK: [MessageHandler(filters.TEXT & ~filters.COMMAND, give_task_mark)],
        TASK_DOC: [MessageHandler(filters.Document.ALL, give_task_doc), MessageHandler(filters.TEXT & ~filters.COMMAND, give_task_doc), CommandHandler("skip", skip_task_doc)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)


# ── /notes ─────────────────────────────────────────────────────────


async def notes_list(update: Update, _context):
    from db.database import async_session
    from models.models import Note

    user = await get_user(str(update.effective_user.id))
    if not user:
        await update.effective_message.reply_text("You need an account first.")
        return

    async with async_session() as session:
        q = select(Note).order_by(Note.created_at.desc())
        if not user.role.value == "admin":
            q = q.where(Note.department == user.department)
        notes = (await session.execute(q)).scalars().all()

    if not notes:
        await update.effective_message.reply_text("No notes found.")
        return

    btns = [InlineKeyboardButton(n.title, callback_data=f"note_{n.id}") for n in notes]
    keyboard = [btns[i:i+2] for i in range(0, len(btns), 2)]
    await update.effective_message.reply_text(
        "Select a note:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def note_detail_callback(update: Update, _context):
    from db.database import async_session
    from models.models import Note

    query = update.callback_query
    await query.answer()

    note_id = int(query.data.split("_")[1])
    async with async_session() as session:
        n = (await session.execute(select(Note).where(Note.id == note_id))).scalar_one_or_none()

    if not n:
        await query.message.reply_text("Note not found.")
        return

    lines = [f"*{n.title}*", f"_{n.created_at.date()}_"]
    if n.content:
        lines.append(f"\n📝 {n.content}")
    await query.message.reply_markdown("\n".join(lines))

    if n.file_id:
        try:
            await query.message.reply_document(
                document=n.file_id,
                filename=n.file_name or n.file_id,
                caption=f"📎 {n.title}",
            )
        except Exception as e:
            logger.error("Failed to send note file (file_id): error=%s", e)
    elif n.file_url:
        try:
            from bot.files import migrate_cloudinary_file
            result = await migrate_cloudinary_file(n.file_url, n.file_name)
            if result:
                fid, fname = result
                from db.database import async_session
                from models.models import Note
                async with async_session() as session:
                    async with session.begin():
                        obj = await session.get(Note, n.id)
                        if obj:
                            obj.file_id = fid
                            obj.file_name = fname
                await query.message.reply_document(
                    document=fid,
                    filename=fname,
                    caption=f"📎 {n.title}",
                )
        except Exception as e:
            logger.error("Failed to send note file: url=%s error=%s", n.file_url, e)
            await query.message.reply_text(f"⚠️ Could not send attachment.")
    else:
        await query.message.reply_text("ℹ️ No attachment for this note.")


# ── /givenotes ─────────────────────────────────────────────────────


async def give_note_start(update: Update, _context):
    from models.models import Role

    user = await get_user(str(update.effective_user.id))
    if not user or user.role not in (Role.admin, Role.instructor):
        await update.message.reply_text("Only admins and instructors can create notes.")
        return ConversationHandler.END

    await update.message.reply_text("Send the *note title*:")
    return NOTE_TITLE


async def give_note_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["note_title"] = update.message.text
    await update.message.reply_text(
        "Send the *content* (or send `/skip` to skip):"
    )
    return NOTE_CONTENT


async def skip_note_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["note_content"] = None
    await update.message.reply_text(
        "Send the *department* (ISM / SWE / CGWD / EDM / CSNW / DBM / CNWS / NS)\n"
        "Or send `/skip` to use your own department."
    )
    return NOTE_DEPT


async def give_note_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["note_content"] = update.message.text
    await update.message.reply_text(
        "Send the *department* (ISM / SWE / CGWD / EDM / CSNW / DBM / CNWS / NS)\n"
        "Or send `/skip` to use your own department."
    )
    return NOTE_DEPT


async def skip_note_dept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(str(update.effective_user.id))
    context.user_data["note_dept"] = user.department
    await update.message.reply_text("Upload the *file* (or send `/skip` to skip):")
    return NOTE_FILE


async def give_note_dept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from models.models import Department

    try:
        context.user_data["note_dept"] = Department(update.message.text.strip().upper())
    except ValueError:
        await update.message.reply_text("Invalid department. Try: ISM / SWE / CGWD / EDM / CSNW / DBM / CNWS / NS")
        return NOTE_DEPT

    await update.message.reply_text(
        "Upload the *file* (or send `/skip` to skip):"
    )
    return NOTE_FILE


async def skip_note_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from db.database import async_session
    from models.models import Note

    user = await get_user(str(update.effective_user.id))
    async with async_session() as session:
        async with session.begin():
            session.add(Note(
                title=context.user_data["note_title"],
                content=context.user_data["note_content"],
                department=context.user_data["note_dept"],
                file_url=None,
                uploaded_by=user.id,
            ))

    context.user_data.clear()
    await update.message.reply_text("✅ Note created successfully!")
    return ConversationHandler.END


async def give_note_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from db.database import async_session
    from models.models import Note

    user = await get_user(str(update.effective_user.id))

    file_id = None
    file_name = None
    file_url_for_legacy = None
    if update.message.document:
        file = await context.bot.get_file(update.message.document.file_id)
        file_bytes = await file.download_as_bytearray()
        from bot.files import upload_file_to_group
        file_id, file_name = await upload_file_to_group(bytes(file_bytes), update.message.document.file_name or "note")
        file_url_for_legacy = file_id

    async with async_session() as session:
        async with session.begin():
            note = Note(
                title=context.user_data["note_title"],
                content=context.user_data["note_content"],
                department=context.user_data["note_dept"],
                file_url=file_url_for_legacy,
                file_id=file_id,
                file_name=file_name,
                uploaded_by=user.id,
            )
            session.add(note)

    context.user_data.clear()
    await update.message.reply_text("✅ Note created successfully!")
    return ConversationHandler.END


give_note_conv = ConversationHandler(
    entry_points=[CommandHandler("givenotes", give_note_start)],
    states={
        NOTE_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, give_note_title)],
        NOTE_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, give_note_content), CommandHandler("skip", skip_note_content)],
        NOTE_DEPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, give_note_dept), CommandHandler("skip", skip_note_dept)],
        NOTE_FILE: [MessageHandler(filters.Document.ALL, give_note_file), MessageHandler(filters.TEXT & ~filters.COMMAND, give_note_file), CommandHandler("skip", skip_note_file)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

IMAGE_PHOTO = 0


async def image_start(update: Update, _context):
    reply = reply_fn(update)
    await reply("Send me a photo to set as your profile picture.")
    return IMAGE_PHOTO


async def image_handle_photo(update: Update, context):
    from bot.files import upload_file_to_group

    telegram_id = str(update.effective_user.id)
    reply = reply_fn(update)

    user = await get_user(telegram_id)
    if not user:
        await reply("You need an account first. Use /start to create one.")
        return ConversationHandler.END

    photo = update.message.photo[-1]
    file = await photo.get_file()
    photo_bytes = await file.download_as_bytearray()

    file_id, _ = await upload_file_to_group(
        bytes(photo_bytes),
        f"profile_{telegram_id}.jpg",
    )

    from db.database import async_session
    from models.models import User as UserModel

    async with async_session() as session:
        async with session.begin():
            u = (await session.execute(select(UserModel).where(UserModel.telegram_id == telegram_id))).scalar_one_or_none()
            if u:
                u.image = file_id

    await reply("Profile picture updated!")
    return ConversationHandler.END


image_conv = ConversationHandler(
    entry_points=[CommandHandler("image", image_start)],
    states={
        IMAGE_PHOTO: [MessageHandler(filters.PHOTO, image_handle_photo)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# ── User CSV Export ──────────────────────────────────────────────

CSV_FILTER_OPTIONS = {
    "role": [("Intern", "intern"), ("Instructor", "instructor"), ("Admin", "admin")],
    "dept": [("ISM", "ISM"), ("SWE", "SWE"), ("CGWD", "CGWD"), ("EDM", "EDM"),
             ("CSNW", "CSNW"), ("DBM", "DBM"), ("CNWS", "CNWS"), ("NS", "NS")],
    "group": [("A", "A"), ("B", "B")],
    "gender": [("Male", "male"), ("Female", "female")],
    "fees": [("Paid in full", "paid"), ("Not paid", "unpaid"),
             ("Remaining > 0", "remaining"), ("Remaining >= 5000", "remaining_5000"),
             ("Remaining < 5000", "remaining_under")],
    "linked": [("Linked", "linked"), ("Pending", "pending")],
}

CSV_FILTER_LABELS = {
    "role": "Role", "dept": "Department", "group": "Group",
    "gender": "Gender", "fees": "Fee Status", "linked": "Linked",
}


async def csv_user_start(update: Update, context):
    from models.models import Role

    user = await get_user(str(update.effective_user.id))
    if not user or user.role not in (Role.admin, Role.instructor):
        await update.message.reply_text("Only instructors and admins can use this command.")
        return
    context.user_data["csv_filters"] = {}
    await _csv_show_menu(update, context, edit=False)


async def _csv_show_menu(update, context, edit=True):
    filters = context.user_data.get("csv_filters", {})
    text = "*User CSV Export*\nSelect filters below, then generate."
    if filters:
        text += "\n\n*Active filters:*"
        for k, v in filters.items():
            label = CSV_FILTER_LABELS.get(k, k)
            text += f"\n• {label}: `{v}`"

    rows = []
    for key, label in CSV_FILTER_LABELS.items():
        rows.append([InlineKeyboardButton(
            f"{label}: {filters.get(key, 'Any')}",
            callback_data=f"csv:filter:{key}",
        )])
    rows.append([InlineKeyboardButton("📥 Generate CSV", callback_data="csv:generate")])

    msg = update.callback_query.message if edit else update.message
    kwargs = {"parse_mode": "Markdown", "reply_markup": InlineKeyboardMarkup(rows)}
    if edit:
        await msg.edit_text(text, **kwargs)
    else:
        await msg.reply_text(text, **kwargs)


async def csv_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "csv:generate":
        await _csv_generate(update, context)
        return

    if data.startswith("csv:filter:"):
        filter_name = data.split(":", 2)[2]
        options = CSV_FILTER_OPTIONS.get(filter_name, [])
        if not options:
            return
        text = f"Select *{CSV_FILTER_LABELS.get(filter_name, filter_name)}*:"
        keyboard = [
            [InlineKeyboardButton(f"◀ Back", callback_data="csv:menu")],
        ]
        for lbl, val in options:
            keyboard.append([InlineKeyboardButton(lbl, callback_data=f"csv:set:{filter_name}:{val}")])
        await query.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("csv:set:"):
        parts = data.split(":", 2)
        rest = parts[2]
        filter_name, filter_val = rest.split(":", 1)
        context.user_data.setdefault("csv_filters", {})[filter_name] = filter_val
        await _csv_show_menu(update, context)

    if data == "csv:menu":
        await _csv_show_menu(update, context)


async def _csv_generate(update, context):
    import csv
    import io

    from uuid import uuid4

    from sqlalchemy import select

    from db.database import async_session
    from models.models import User as UserModel

    query = update.callback_query
    filters = context.user_data.get("csv_filters", {})

    stmt = select(UserModel)
    if "role" in filters:
        from models.models import Role
        stmt = stmt.where(UserModel.role == Role(filters["role"]))
    if "dept" in filters:
        from models.models import Department
        stmt = stmt.where(UserModel.department == Department(filters["dept"]))
    if "group" in filters:
        from models.models import Group
        stmt = stmt.where(UserModel.group == Group(filters["group"]))
    if "gender" in filters:
        from models.models import Gender
        stmt = stmt.where(UserModel.gender == Gender(filters["gender"]))
    if "fees" in filters:
        val = filters["fees"]
        if val == "paid":
            stmt = stmt.where(UserModel.fees_paid >= UserModel.total_fees)
        elif val == "unpaid":
            stmt = stmt.where((UserModel.fees_paid == None) | (UserModel.fees_paid == 0))
        elif val == "remaining":
            stmt = stmt.where(UserModel.total_fees - UserModel.fees_paid > 0)
        elif val == "remaining_5000":
            stmt = stmt.where(UserModel.total_fees - UserModel.fees_paid >= 5000)
        elif val == "remaining_under":
            stmt = stmt.where(
                (UserModel.total_fees - UserModel.fees_paid > 0) &
                (UserModel.total_fees - UserModel.fees_paid < 5000)
            )
    if "linked" in filters:
        if filters["linked"] == "linked":
            stmt = stmt.where(~UserModel.telegram_id.startswith("pending_"))
        else:
            stmt = stmt.where(UserModel.telegram_id.startswith("pending_"))

    await query.message.edit_text("Generating CSV…")

    async with async_session() as session:
        users = (await session.execute(stmt.order_by(UserModel.id))).scalars().all()

    buf = io.StringIO()
    w = csv.writer(buf)
    headers = ["ID", "Name", "Surname", "Phone", "Telegram ID", "Gender", "Role",
               "Department", "Group", "School", "DOB", "Quarter", "Fees Paid",
               "Total Fees", "Linked", "Image"]
    w.writerow(headers)
    for u in users:
        w.writerow([
            u.id, u.name, u.surname, u.phone, u.telegram_id,
            u.gender.value, u.role.value, u.department.value,
            u.group.value if u.group else "", u.school, str(u.dob),
            u.quarter or "", float(u.fees_paid or 0), float(u.total_fees or 0),
            "Yes" if not u.telegram_id.startswith("pending_") else "No",
            u.image or "",
        ])

    csv_bytes = buf.getvalue().encode("utf-8")
    buf_io = io.BytesIO(csv_bytes)
    buf_io.name = f"users_{uuid4().hex[:8]}.csv"
    await query.message.reply_document(document=buf_io, filename=buf_io.name, caption=f"📊 Users: {len(users)} rows")
    del context.user_data["csv_filters"]


# ── Attendance CSV Export ────────────────────────────────────────

async def attend_csv_start(update: Update, context):
    from models.models import Role

    user = await get_user(str(update.effective_user.id))
    if not user or user.role not in (Role.admin, Role.instructor):
        await update.message.reply_text("Only instructors and admins can use this command.")
        return
    context.user_data["acsv_filters"] = {}
    await _acsv_show_menu(update, context, edit=False)


ACSV_FILTER_LABELS = {
    "group": "Group",
    "dept": "Department",
    "period": "Period",
}

ACSV_PERIOD_OPTIONS = [
    ("Last 7 days", "7d"),
    ("Last 30 days", "30d"),
    ("All time", "all"),
]


async def _acsv_show_menu(update, context, edit=True):
    filters = context.user_data.get("acsv_filters", {})
    text = "*Attendance CSV Export*\nSelect filters, then generate."
    if filters:
        text += "\n\n*Active filters:*"
        for k, v in filters.items():
            label = ACSV_FILTER_LABELS.get(k, k)
            text += f"\n• {label}: `{v}`"

    rows = [
        [InlineKeyboardButton(f"Group: {filters.get('group', 'Any')}", callback_data="acsv:filter:group")],
        [InlineKeyboardButton(f"Department: {filters.get('dept', 'Any')}", callback_data="acsv:filter:dept")],
        [InlineKeyboardButton(f"Period: {filters.get('period', 'All time')}", callback_data="acsv:filter:period")],
        [InlineKeyboardButton("📥 Generate CSV", callback_data="acsv:generate")],
    ]

    msg = update.callback_query.message if edit else update.message
    kwargs = {"parse_mode": "Markdown", "reply_markup": InlineKeyboardMarkup(rows)}
    if edit:
        await msg.edit_text(text, **kwargs)
    else:
        await msg.reply_text(text, **kwargs)


async def acsv_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "acsv:generate":
        await _acsv_generate(update, context)
        return

    if data.startswith("acsv:filter:"):
        filter_name = data.split(":", 2)[2]
        text = f"Select *{ACSV_FILTER_LABELS.get(filter_name, filter_name)}*:"

        if filter_name == "group":
            options = [("A", "A"), ("B", "B")]
        elif filter_name == "dept":
            from models.models import Department
            options = [(d.value, d.value) for d in Department]
        elif filter_name == "period":
            options = ACSV_PERIOD_OPTIONS
        else:
            return

        keyboard = [[InlineKeyboardButton("◀ Back", callback_data="acsv:menu")]]
        for lbl, val in options:
            keyboard.append([InlineKeyboardButton(lbl, callback_data=f"acsv:set:{filter_name}:{val}")])
        await query.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("acsv:set:"):
        parts = data.split(":", 2)
        rest = parts[2]
        filter_name, filter_val = rest.split(":", 1)
        context.user_data.setdefault("acsv_filters", {})[filter_name] = filter_val
        await _acsv_show_menu(update, context)

    if data == "acsv:menu":
        await _acsv_show_menu(update, context)


async def _acsv_generate(update, context):
    import csv
    import io
    from datetime import datetime, timedelta
    from uuid import uuid4

    from sqlalchemy import select

    from db.database import async_session
    from models.models import Attendance, InternAttendance, User as UserModel

    query = update.callback_query
    filters = context.user_data.get("acsv_filters", {})

    stmt = (
        select(Attendance.date, Attendance.group, UserModel.name, UserModel.surname,
               UserModel.phone, UserModel.department, InternAttendance.enter_at,
               InternAttendance.left_at)
        .join(InternAttendance, InternAttendance.attendance_id == Attendance.id)
        .join(UserModel, UserModel.id == InternAttendance.user_id)
    )

    if "group" in filters:
        from models.models import Group
        stmt = stmt.where(Attendance.group == Group(filters["group"]))
    if "dept" in filters:
        from models.models import Department
        stmt = stmt.where(UserModel.department == Department(filters["dept"]))
    if "period" in filters:
        days = {"7d": 7, "30d": 30}.get(filters["period"])
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            stmt = stmt.where(Attendance.date >= cutoff.date())

    await query.message.edit_text("Generating CSV…")

    async with async_session() as session:
        rows_data = (await session.execute(stmt.order_by(Attendance.date.desc(), Attendance.group))).all()

    buf = io.StringIO()
    w = csv.writer(buf)
    headers = ["Date", "Group", "Name", "Surname", "Phone", "Department", "Enter At", "Left At"]
    w.writerow(headers)
    for r in rows_data:
        w.writerow([
            str(r.date), r.group.value, r.name, r.surname, r.phone,
            r.department.value, str(r.enter_at), str(r.left_at or ""),
        ])

    csv_bytes = buf.getvalue().encode("utf-8")
    buf_io = io.BytesIO(csv_bytes)
    buf_io.name = f"attendance_{uuid4().hex[:8]}.csv"
    await query.message.reply_document(document=buf_io, filename=buf_io.name, caption=f"📊 Attendance: {len(rows_data)} rows")
    del context.user_data["acsv_filters"]


handlers = [
    sync_conv,
    give_task_conv,
    submit_conv,
    give_note_conv,
    image_conv,
    CommandHandler("me", me),
    CommandHandler("info", announcements),
    CommandHandler("qr", qr_command),
    CommandHandler("helpInfo", help_info),
    CommandHandler("helpinfo", help_info),
    CommandHandler("userInfo", user_info),
    CommandHandler("userinfo", user_info),
    CommandHandler("taskInfo", task_info),
    CommandHandler("taskinfo", task_info),
    CommandHandler("notes", notes_list),
    CommandHandler("dashboard", dashboard),
    CommandHandler("dash", dashboard),
    CommandHandler("link", link_cmd),
    CommandHandler("db", db_backup),
    MessageHandler(filters.CONTACT, handle_contact),
    CallbackQueryHandler(info_detail_callback, pattern=r"^info_\d+$"),
    CallbackQueryHandler(info_callback, pattern="^info_"),
    CallbackQueryHandler(task_detail_callback, pattern="^task_"),
    CallbackQueryHandler(note_detail_callback, pattern="^note_"),
    CommandHandler("usercsv", csv_user_start),
    CommandHandler("attendcsv", attend_csv_start),
    CallbackQueryHandler(csv_callback, pattern="^csv:"),
    CallbackQueryHandler(acsv_callback, pattern="^acsv:"),
]
