import logging

from sqlalchemy import func, select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, WebAppInfo
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

from bot.handlers.common import get_user, format_user_info, reply_fn, reply_md_fn, logger, HELP_INFO_TEXT
from config import settings

logger = logging.getLogger(__name__)


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
            try:
                await update.effective_message.reply_document(
                    document=image_id,
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
        phone = "+237" + phone
    caller_id = str(update.effective_user.id)
    contact_user_id = str(contact.user_id)

    from db.database import async_session
    from models.models import User

    async with async_session() as session:
        async with session.begin():
            user = (
                await session.execute(select(User).where(User.phone == phone))
            ).scalar_one_or_none()

            # If this is the caller's own contact, trust it and link/update
            if caller_id == contact_user_id:
                if user:
                    user.telegram_id = caller_id
                    await update.message.reply_text(
                        f"Linked! Welcome back {user.name} {user.surname}.",
                        reply_markup=ReplyKeyboardRemove(),
                    )
                    return
                else:
                    await update.message.reply_text(
                        "No account found with this phone number.",
                        reply_markup=ReplyKeyboardRemove(),
                    )
                    return

            if not user:
                await update.message.reply_text(
                    "No account found with this phone number.",
                    reply_markup=ReplyKeyboardRemove(),
                )
                return

            if user.telegram_id and not user.telegram_id.startswith("pending_") and user.telegram_id != caller_id:
                old_tid = user.telegram_id
                user.telegram_id = caller_id
                try:
                    from bot.router import application
                    if application:
                        await application.bot.send_message(
                            chat_id=int(old_tid),
                            text="⚠️ Your phone number has been linked to a new account. If this wasn't you, please contact support.",
                        )
                except Exception:
                    pass
                await update.message.reply_text(
                    f"Linked! Welcome {user.name} {user.surname}.",
                    reply_markup=ReplyKeyboardRemove(),
                )
                return

            if user.telegram_id == caller_id:
                await update.message.reply_text(
                    "Already linked!",
                    reply_markup=ReplyKeyboardRemove(),
                )
                return

            user.telegram_id = caller_id

    await update.message.reply_text(
        f"Linked! Welcome {user.name} {user.surname}.",
        reply_markup=ReplyKeyboardRemove(),
    )


views_handlers = [
    CommandHandler("me", me),
    CommandHandler("info", announcements),
    CommandHandler("helpInfo", help_info),
    CommandHandler("helpinfo", help_info),
    CommandHandler("userInfo", user_info),
    CommandHandler("userinfo", user_info),
    CommandHandler("taskInfo", task_info),
    CommandHandler("taskinfo", task_info),
    CommandHandler("dashboard", dashboard),
    CommandHandler("dash", dashboard),
    CommandHandler("link", link_cmd),
    MessageHandler(filters.CONTACT, handle_contact),
    CallbackQueryHandler(info_detail_callback, pattern=r"^info_\d+$"),
    CallbackQueryHandler(info_callback, pattern="^info_"),
    CallbackQueryHandler(task_detail_callback, pattern="^task_"),
]
