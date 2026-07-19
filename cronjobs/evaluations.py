import asyncio
import logging
from datetime import date

from sqlalchemy import select

from controllers.evaluationController import get_evaluations, get_missing_evaluations
from db.database import SyncSession
from models.enums import Role
from models.user import User

logger = logging.getLogger(__name__)


async def eval_summary():
    from cronjobs.scheduler import get_bot

    today = date.today()
    if today.weekday() == 6:
        return

    loop = asyncio.get_running_loop()

    def _get_data():
        session = SyncSession()
        try:
            evals = get_evaluations(session, today)
            missing = get_missing_evaluations(session, today)
            return evals, missing
        finally:
            session.close()

    evals, missing = await loop.run_in_executor(None, _get_data)

    bot = get_bot()
    if not bot:
        logger.warning("Bot not available, skipping eval summary")
        return

    def _get_staff():
        session = SyncSession()
        try:
            rows = session.execute(
                select(User.telegram_id, User.name, User.surname)
                .where(
                    User.role.in_([Role.admin, Role.super_admin, Role.instructor]),
                    User.telegram_id.isnot(None),
                    ~User.telegram_id.like("pending_%"),
                )
            ).all()
            return [(int(r.telegram_id), r.name, r.surname) for r in rows]
        finally:
            session.close()

    staff = await loop.run_in_executor(None, _get_staff)
    if not staff:
        logger.info("No staff to notify about eval summary")
        return

    eval_count = len(evals)
    missing_count = len(missing)

    missing_text = ""
    if missing:
        names = [f"{m['name']} {m['surname']}" for m in missing]
        missing_text = f"\n\n⚠️ *Unevaluated interns ({missing_count}):*\n" + "\n".join(f"• {n}" for n in names)

    text = (
        f"📋 *Daily Evaluation Summary — {today.isoformat()}*\n\n"
        f"✅ Evaluated: *{eval_count}* intern{'s' if eval_count != 1 else ''}"
        f"{missing_text}"
    )

    for tid, name, surname in staff:
        try:
            await bot.send_message(chat_id=tid, text=text, parse_mode="Markdown")
        except Exception as e:
            logger.warning("Failed to send eval summary to %s: %s", tid, e)

    logger.info("Eval summary sent to %d staff members", len(staff))


async def eval_start_reminder():
    from cronjobs.scheduler import get_bot

    today = date.today()
    if today.weekday() == 6:
        return

    loop = asyncio.get_running_loop()

    def _get_interns():
        session = SyncSession()
        try:
            rows = session.execute(
                select(User.telegram_id, User.name, User.surname, User.is_active)
                .where(
                    User.role == Role.intern,
                    User.telegram_id.isnot(None),
                    ~User.telegram_id.like("pending_%"),
                )
            ).all()
            return [(int(r.telegram_id), r.name, r.surname, r.is_active) for r in rows]
        finally:
            session.close()

    interns = await loop.run_in_executor(None, _get_interns)
    if not interns:
        logger.info("No interns to notify about evaluations")
        return

    bot = get_bot()
    if not bot:
        logger.warning("Bot not available, skipping eval start reminder")
        return

    active_count = sum(1 for _, _, _, active in interns if active)
    inactive_count = sum(1 for _, _, _, active in interns if not active)

    for tid, name, surname, active in interns:
        try:
            if active:
                text = (
                    f"📋 *Daily Evaluations Start Today!*\n\n"
                    f"Dear {name} {surname},\n\n"
                    f"Starting today, you will be evaluated daily on the following criteria:\n"
                    f"• Punctuality\n"
                    f"• Professionalism\n"
                    f"• Dressing\n"
                    f"• Conduct\n"
                    f"• Teamwork\n"
                    f"• Participation\n"
                    f"• Leadership\n"
                    f"• Presentation\n"
                    f"• Communication\n\n"
                    f"Each criterion is scored 1–5. Make sure to give your best every day! 💪"
                )
            else:
                text = (
                    f"⚠️ *Important: Evaluation & Account Issue*\n\n"
                    f"Dear {name} {surname},\n\n"
                    f"Daily evaluations start today, but your account is currently marked as **inactive**.\n\n"
                    f"This may negatively impact your evaluation form and training record.\n"
                    f"Please contact the admin immediately to resolve this issue and reactivate your account."
                )
            await bot.send_message(chat_id=tid, text=text, parse_mode="Markdown")
        except Exception as e:
            logger.warning("Failed to send eval reminder to %s: %s", tid, e)

    logger.info(
        "Eval start reminder sent to %d interns (%d active, %d inactive)",
        len(interns), active_count, inactive_count,
    )
