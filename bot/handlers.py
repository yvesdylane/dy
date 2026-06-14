import logging

from sqlalchemy import select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler

from config import settings

logger = logging.getLogger(__name__)


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


async def info(update: Update, _context):
    telegram_id = str(update.effective_user.id)

    try:
        from db.database import async_session
        from models.models import User

        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()

        if user:
            text = format_user_info(user)
            await update.message.reply_markdown(text)
        else:
            mini_app_url = f"{settings.mini_app_url.rstrip('/')}/app"
            button = InlineKeyboardButton("Create Account", url=mini_app_url)
            keyboard = InlineKeyboardMarkup([[button]])
            await update.message.reply_text(
                "You don't have an account yet. Tap the button below to create one.",
                reply_markup=keyboard,
            )
    except Exception as e:
        logger.error("Info command failed: %s", e)
        await update.message.reply_text("An error occurred. Please try again later.")


handlers = [CommandHandler("info", info)]
