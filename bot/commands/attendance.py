import logging
from datetime import date, datetime

from sqlalchemy import select
from telegram import Update
from telegram.ext import MessageHandler, filters

from controllers.passController import use_code
from db.database import get_sync_db
from models.attendance import Attendance, InternAttendance
from models.enums import Group, Role
from models.user import User

logger = logging.getLogger(__name__)


async def handle_attendance_code(update: Update, _context):
    code_str = update.message.text.lstrip("/").upper()
    telegram_id = str(update.effective_user.id)

    with get_sync_db() as session:
        now = datetime.utcnow()
        today = date.today()

        weekday = today.weekday()
        if weekday == 6:
            await update.message.reply_text("No attendance on Sundays.")
            return

        today_group = Group.A if weekday in (0, 2, 4) else Group.B

        user = session.execute(
            select(User).where(User.telegram_id == telegram_id)
        ).scalar_one_or_none()

        if not user:
            await update.message.reply_text("You need to create an account first. Use /start.")
            return

        if user.group != today_group:
            await update.message.reply_text(
                f"Today is Group {today_group.value}, you are Group {user.group.value}."
            )
            return

        fees_paid = float(user.fees_paid or 0)
        if user.role == Role.intern and fees_paid < 20000:
            from config import settings

            if date.today() >= settings.fee_block_start_date:
                await update.message.reply_text(
                    f"⚠️ Your fees ({fees_paid:,.0f} FCFA) are below 20,000 FCFA. "
                    "Starting this week, attendance is blocked until fees are "
                    "resolved. Contact the admin."
                )
                return
            else:
                await update.message.reply_text(
                    f"⚠️ Reminder: your fees ({fees_paid:,.0f} FCFA) are below 20,000 FCFA. "
                    "Starting next week you won't be able to take attendance. "
                    "Please settle your fees."
                )

        valid, mode = use_code(code_str)
        if not valid:
            await update.message.reply_text("Invalid or expired code.")
            return

        att = session.execute(
            select(Attendance).where(
                Attendance.date == today,
                Attendance.group == today_group,
            )
        ).scalar_one_or_none()
        if not att:
            att = Attendance(date=today, group=today_group)
            session.add(att)
            session.flush()

        entry = session.execute(
            select(InternAttendance).where(
                InternAttendance.attendance_id == att.id,
                InternAttendance.user_id == user.id,
            )
        ).scalar_one_or_none()

        if not entry:
            entry = InternAttendance(
                attendance_id=att.id,
                user_id=user.id,
            )
            session.add(entry)

        if mode == "entry":
            entry.enter_at = now
            msg = f"✅ Entry marked at {now.strftime('%H:%M')}"
        elif mode == "exit":
            entry.left_at = now
            msg = f"✅ Exit marked at {now.strftime('%H:%M')}"

        await update.message.reply_text(msg)


attendance_handlers = [
    MessageHandler(filters.Regex(r"^/[A-Z0-9]{5}$"), handle_attendance_code),
]
