import asyncio
import logging

from sqlalchemy import select

from db.database import SyncSession
from models.enums import Group, Role
from models.user import User

logger = logging.getLogger(__name__)


async def fee_reminder():
    from cronjobs.scheduler import get_bot

    loop = asyncio.get_running_loop()
    interns = await loop.run_in_executor(None, _sync_get_interns)
    if not interns:
        logger.info("No interns to remind about fees today")
        return

    bot = get_bot()
    if not bot:
        logger.warning("Bot not available, skipping fee reminders")
        return

    for name, surname, tid, paid, total in interns:
        try:
            await bot.send_message(
                chat_id=tid,
                text=(
                    f"⚠️ *Fee Reminder*\n\n"
                    f"Dear {name} {surname},\n"
                    f"Your current fees paid is *{paid:,.0f} FCFA* out of *{total:,.0f} FCFA*.\n\n"
                    f"Starting next week, you will not be able to take attendance "
                    f"if your fees are not cleared.\n"
                    f"Please contact the admin to resolve this issue."
                ),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning("Failed to send fee reminder to %s: %s", tid, e)


def _sync_get_interns():
    from datetime import date

    today = date.today()
    if today.weekday() == 6:
        return []

    group = Group.A if today.weekday() in (0, 2, 4) else Group.B

    session = SyncSession()
    try:
        rows = session.execute(
            select(User.name, User.surname, User.telegram_id, User.fees_paid, User.total_fees)
            .where(
                User.role == Role.intern,
                User.group == group,
                User.fees_paid < 15000,
                User.telegram_id.isnot(None),
                ~User.telegram_id.like("pending_%"),
            )
        ).all()
        return [
            (
                r.name,
                r.surname,
                int(r.telegram_id),
                float(r.fees_paid or 0),
                float(r.total_fees or 0),
            )
            for r in rows
        ]
    finally:
        session.close()
