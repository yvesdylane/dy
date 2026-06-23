import logging

from sqlalchemy import select
from telegram import Update

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
