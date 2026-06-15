import logging

from sqlalchemy import func, select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, WebAppInfo
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

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
    reply = reply_md_fn(update)

    if not user:
        mini_app_url = f"{settings.mini_app_url.rstrip('/')}/app"
        url_with_id = f"{mini_app_url}?telegram_id={telegram_id}"
        button = InlineKeyboardButton("Create Account", web_app=WebAppInfo(url=url_with_id))
        keyboard = InlineKeyboardMarkup([[button]])
        await reply(
            "You don't have an account yet. Tap the button below to create one.",
            reply_markup=keyboard,
        )
        return

    text = format_user_info(user)
    text += "\n\nUse /helpInfo to explore more info commands."
    await reply(text)


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
    from db.database import async_session
    from models.models import Department, Role, Task

    reply = reply_md_fn(update)

    me = await get_user(telegram_id)
    if not me:
        await reply("You need an account first.")
        return

    async with async_session() as session:
        q = select(Task)
        if me.role == Role.intern:
            q = q.where(Task.department == me.department)
        q = q.order_by(Task.submission_deadline)
        tasks = (await session.execute(q)).scalars().all()

    if not tasks:
        await reply("No tasks found.")
        return

    scope = f"department *{me.department.value}*" if me.role == Role.intern else "all departments"
    lines = [f"*Tasks ({scope}):*"]
    for t in tasks:
        lines.append(f"\n• *{t.name}* — due {t.submission_deadline.date()}")
    await reply("\n".join(lines))


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
            await update.message.reply_text("No announcements yet.")
            return

        lines = ["*📢 Announcements:*"]
        for item in items:
            lines.append(f"\n*{item.title}*")
            lines.append(f"{item.content[:200]}")
            lines.append(f"_{item.created_at.date()}_")

        await update.message.reply_markdown("\n".join(lines))
    except Exception as e:
        logger.error("Info command failed: %s", e)
        reply = reply_fn(update)
        await reply("An error occurred.")


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
        "info_notes": lambda tid, u: reply_fn(u)("Notes info coming soon."),
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

            if user.telegram_id and user.telegram_id != telegram_id:
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


handlers = [
    CommandHandler("me", me),
    CommandHandler("info", announcements),
    CommandHandler("qr", qr_command),
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
    CallbackQueryHandler(info_callback, pattern="^info_"),
]
