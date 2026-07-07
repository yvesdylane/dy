import logging

from sqlalchemy import select
from telegram import Update
from telegram.helpers import escape_markdown

from db.database import get_sync_db
from models.user import User

logger = logging.getLogger(__name__)

ROLE_DISPLAY = {
    "super_admin": "Super Admin",
    "admin": "Admin",
    "instructor": "Instructor",
    "intern": "Intern",
}


def get_user_sync(telegram_id: str) -> User | None:
    with get_sync_db() as session:
        return session.execute(
            select(User).where(User.telegram_id == telegram_id)
        ).scalar_one_or_none()


def format_user_info(user) -> str:
    def esc(value) -> str:
        return escape_markdown(str(value), version=1)

    role_label = ROLE_DISPLAY.get(user.role.value, user.role.value)

    lines = [
        f"*Name:* {esc(user.name)} {esc(user.surname)}",
        f"*Phone:* {esc(user.phone)}",
        f"*Telegram ID:* `{esc(user.telegram_id)}`",
        f"*Gender:* {esc(user.gender.value)}",
        f"*Role:* {role_label}",
        f"*Department:* {esc(user.department.value)}",
        f"*School:* {esc(user.school)}",
        f"*DOB:* {esc(user.dob)}",
    ]
    if user.group:
        lines.insert(5, f"*Group:* {esc(user.group.value)}")
    if user.role.value == "intern":
        lines.append(f"*Quarter:* {esc(user.quarter or 'N/A')}")
        lines.append(f"*Fees Paid:* {esc(user.fees_paid or 0)}")
        lines.append(f"*Total Fees:* {esc(user.total_fees or 40000)}")
    return "\n".join(lines)


def reply_fn(update: Update):
    if update.callback_query:
        return update.callback_query.message.reply_text
    return update.message.reply_text


def reply_md_fn(update: Update):
    if update.callback_query:
        return update.callback_query.message.reply_markdown
    return update.message.reply_markdown
