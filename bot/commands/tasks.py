import logging
from datetime import datetime

from sqlalchemy import select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters

from bot.common import INACTIVE_MSG, get_user_sync
from bot.files import upload_file_to_group
from db.database import get_sync_db
from models.task import Task, TaskSubmission

logger = logging.getLogger(__name__)

SUBMIT_SELECT, SUBMIT_FILE, SUBMIT_URL = range(3)


async def _cancel(update: Update, _context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


async def submit_start(update: Update, _context):
    user = get_user_sync(str(update.effective_user.id))
    if not user:
        await update.message.reply_text("You need an account first.")
        return ConversationHandler.END
    if not user.is_active:
        await update.message.reply_text(INACTIVE_MSG)
        return ConversationHandler.END

    now = datetime.utcnow()
    with get_sync_db() as session:
        tasks = session.execute(
            select(Task).where(
                Task.department == user.department,
                Task.submission_deadline >= now,
            ).order_by(Task.submission_deadline)
        ).scalars().all()

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


async def submit_select(update: Update, context):
    query = update.callback_query
    await query.answer()
    task_id = int(query.data.split("_")[1])

    with get_sync_db() as session:
        t = session.execute(select(Task).where(Task.id == task_id)).scalar_one_or_none()

    if not t:
        await query.message.reply_text("Task not found.")
        return ConversationHandler.END

    context.user_data["submit_task_id"] = task_id
    await query.message.reply_text(
        f"Upload your submission for *{t.name}*.\n"
        "Send a file, or type /skip to provide a URL instead.",
    )
    return SUBMIT_FILE


async def submit_file(update: Update, context):
    user = get_user_sync(str(update.effective_user.id))
    task_id = context.user_data.get("submit_task_id")
    if not task_id or not user:
        await update.message.reply_text("Something went wrong. Start again with /submit.")
        return ConversationHandler.END

    if update.message.text and update.message.text.strip() == "/skip":
        await update.message.reply_text("Add a URL for your submission (or type /skip to finish):")
        return SUBMIT_URL

    if not update.message.document:
        await update.message.reply_text("Please upload a file, or type /skip to provide a URL.")
        return SUBMIT_FILE

    msg = await update.message.reply_text("Uploading submission...")

    file = await context.bot.get_file(update.message.document.file_id)
    file_bytes = await file.download_as_bytearray()

    file_id, file_name = await upload_file_to_group(
        context.bot, bytes(file_bytes), update.message.document.file_name or "submission"
    )

    context.user_data["submit_file_id"] = file_id
    context.user_data["submit_file_name"] = file_name

    await msg.edit_text("File uploaded! Add a URL for your submission (or type /skip to finish):")
    return SUBMIT_URL


async def submit_url(update: Update, context):
    user = get_user_sync(str(update.effective_user.id))
    task_id = context.user_data.get("submit_task_id")
    if not task_id or not user:
        await update.message.reply_text("Something went wrong. Start again with /submit.")
        return ConversationHandler.END

    url = None
    if update.message.text and update.message.text.strip() != "/skip":
        url = update.message.text.strip()

    msg = await update.message.reply_text("Saving submission...")

    file_id = context.user_data.pop("submit_file_id", None)
    file_name = context.user_data.pop("submit_file_name", None)

    with get_sync_db() as session:
        session.add(TaskSubmission(
            task_id=task_id,
            user_id=user.id,
            submitted_file=file_id,
            file_id=file_id,
            file_name=file_name,
            submitted_url=url,
        ))

    context.user_data.pop("submit_task_id", None)
    await msg.edit_text("✅ Task submitted successfully!")
    return ConversationHandler.END


submit_conv = ConversationHandler(
    entry_points=[CommandHandler("submit", submit_start)],
    states={
        SUBMIT_SELECT: [CallbackQueryHandler(submit_select, pattern="^submit_")],
        SUBMIT_FILE: [
            MessageHandler(filters.Document.ALL, submit_file),
            MessageHandler(filters.Regex(r"^/skip$"), submit_file),
        ],
        SUBMIT_URL: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, submit_url),
            MessageHandler(filters.Regex(r"^/skip$"), submit_url),
        ],
    },
    fallbacks=[CommandHandler("cancel", _cancel)],
)


tasks_handlers = [
    submit_conv,
]
