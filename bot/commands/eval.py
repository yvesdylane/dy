import asyncio
import logging
from datetime import date

from sqlalchemy import select
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from controllers.evaluationController import CRITERIA, get_user_evaluation
from db.database import SyncSession
from models.enums import Role
from models.user import User

logger = logging.getLogger(__name__)


async def handle_eval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    today = date.today()

    def _get():
        session = SyncSession()
        try:
            user = session.execute(
                select(User).where(User.telegram_id == str(user_id))
            ).scalar_one_or_none()
            if user is None:
                return "not_found"
            if user.role != Role.intern:
                return "staff"
            ev = get_user_evaluation(session, user.id, today)
            if ev is None:
                return "no_eval"
            return ev
        finally:
            session.close()

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, _get)

    if result == "not_found":
        await update.message.reply_text("❌ You are not registered. Please register first.")
        return
    if result == "staff":
        await update.message.reply_text("ℹ️ The evaluation system is for interns only.")
        return
    if result == "no_eval":
        await update.message.reply_text(
            "📋 *Daily Evaluation*\n\n"
            "No evaluation found for today. "
            "Evaluations are recorded by your instructor at the end of each training day.",
            parse_mode="Markdown",
        )
        return

    total = result["total"]
    if total >= 40:
        color = "🟢"
    elif total >= 30:
        color = "🟡"
    else:
        color = "🔴"
    max_score = len(CRITERIA) * 5

    lines = [f"📋 *Daily Evaluation — {today.isoformat()}*"]
    lines.append("")
    for c in CRITERIA:
        val = result.get(c)
        display = f"*{val}*/5" if val else "_-_"
        lines.append(f"• {c.capitalize()}: {display}")
    lines.append("")
    lines.append(f"*Total*: {color} {total}/{max_score}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


eval_handlers = [
    CommandHandler("eval", handle_eval),
]
