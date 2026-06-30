from sqlalchemy import select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from previouse.bot.handlers.common import get_user

SUBMIT_SELECT, SUBMIT_FILE, SUBMIT_URL = range(3)
TASK_NAME, TASK_DESC, TASK_DEPT, TASK_DEADLINE, TASK_MARK, TASK_DOC = range(6)


async def cancel(update: Update, _context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ── /submit ───────────────────────────────────────────────────────


async def submit_start(update: Update, _context):
    from datetime import datetime

    from previouse.db.database import async_session
    from previouse.models.models import Task

    user = await get_user(str(update.effective_user.id))
    if not user:
        await update.message.reply_text("You need an account first.")
        return ConversationHandler.END

    now = datetime.utcnow()
    async with async_session() as session:
        tasks = (
            (await session.execute(
                select(Task).where(
                    Task.department == user.department,
                    Task.submission_deadline >= now,
                ).order_by(Task.submission_deadline)
            )).scalars().all()
        )

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


async def submit_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    task_id = int(query.data.split("_")[1])

    from previouse.db.database import async_session
    from previouse.models.models import Task

    async with async_session() as session:
        t = (await session.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()

    if not t:
        await query.message.reply_text("Task not found.")
        return ConversationHandler.END

    context.user_data["submit_task_id"] = task_id
    await query.message.reply_text(
        f"Upload your submission for *{t.name}*.\n"
        "Send a file, or type /skip to provide a URL instead.",
    )
    return SUBMIT_FILE


async def submit_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(str(update.effective_user.id))
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

    from previouse.bot.files import upload_file_to_group
    file_id, file_name = await upload_file_to_group(bytes(file_bytes), update.message.document.file_name or "submission")

    context.user_data["submit_file_id"] = file_id
    context.user_data["submit_file_name"] = file_name

    await msg.edit_text("File uploaded! Add a URL for your submission (or type /skip to finish):")
    return SUBMIT_URL


async def submit_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from previouse.db.database import async_session
    from previouse.models.models import TaskSubmission

    user = await get_user(str(update.effective_user.id))
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

    async with async_session() as session:
        async with session.begin():
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
    fallbacks=[CommandHandler("cancel", cancel)],
)


# ── /givetask ─────────────────────────────────────────────────────


async def give_task_start(update: Update, _context):
    from previouse.models.models import Role

    user = await get_user(str(update.effective_user.id))
    if not user or user.role not in (Role.admin, Role.instructor):
        await update.message.reply_text("Only admins and instructors can create tasks.")
        return ConversationHandler.END

    await update.message.reply_text("Send me the *task name*:")
    return TASK_NAME


async def give_task_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["task_name"] = update.message.text
    await update.message.reply_text("Send me the *description*:")
    return TASK_DESC


async def give_task_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["task_desc"] = update.message.text
    await update.message.reply_text(
        "Send the *department* (ISM / SWE / CGWD / EDM / CSNW / DBM / CNWS / NS)\n"
        "Or send `/skip` to use your own department."
    )
    return TASK_DEPT


async def skip_task_dept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(str(update.effective_user.id))
    context.user_data["task_dept"] = user.department
    await update.message.reply_text("Send the *duration* (e.g. `2 days`, `48 hours`, `1d`, `48h`):")
    return TASK_DEADLINE


async def give_task_dept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from previouse.models.models import Department

    try:
        context.user_data["task_dept"] = Department(update.message.text.strip().upper())
    except ValueError:
        await update.message.reply_text("Invalid department. Try: ISM / SWE / CGWD / EDM / CSNW / DBM / CNWS / NS")
        return TASK_DEPT

    await update.message.reply_text(
        "Send the *duration* (e.g. `2 days`, `48 hours`, `1d`, `48h`):"
    )
    return TASK_DEADLINE


async def give_task_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import re
    from datetime import datetime, timedelta

    text = update.message.text.strip().lower()
    match = re.match(r"(\d+)\s*(h|hr|hours|d|day|days)", text)
    if not match:
        await update.message.reply_text("Invalid format. Use e.g. `2 days`, `48 hours`, `1d`.")
        return TASK_DEADLINE

    amount = int(match.group(1))
    unit = match.group(2)
    if unit in ("h", "hr", "hours"):
        delta = timedelta(hours=amount)
    else:
        delta = timedelta(days=amount)

    context.user_data["task_deadline"] = datetime.utcnow() + delta

    await update.message.reply_text("Send the *total mark*:")
    return TASK_MARK


async def give_task_mark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["task_mark"] = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Invalid number. Send an integer.")
        return TASK_MARK

    await update.message.reply_text(
        "Upload the *supporting document* (or send `/skip` to skip):"
    )
    return TASK_DOC


async def skip_task_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from previouse.db.database import async_session
    from previouse.models.models import Task

    user = await get_user(str(update.effective_user.id))
    async with async_session() as session:
        async with session.begin():
            session.add(Task(
                name=context.user_data["task_name"],
                description=context.user_data["task_desc"],
                department=context.user_data["task_dept"],
                submission_deadline=context.user_data["task_deadline"],
                total_mark_on=context.user_data["task_mark"],
                supporting_doc=None,
                created_by=user.id,
            ))

    context.user_data.clear()
    await update.message.reply_text("✅ Task created successfully!")
    return ConversationHandler.END


async def give_task_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from previouse.db.database import async_session
    from previouse.models.models import Task

    user = await get_user(str(update.effective_user.id))

    doc_url = None
    doc_id = None
    doc_name = None
    if update.message.document:
        file = await context.bot.get_file(update.message.document.file_id)
        file_bytes = await file.download_as_bytearray()
        from previouse.bot.files import upload_file_to_group
        doc_id, doc_name = await upload_file_to_group(bytes(file_bytes), update.message.document.file_name or "task_doc")
        doc_url = doc_id

    async with async_session() as session:
        async with session.begin():
            task = Task(
                name=context.user_data["task_name"],
                description=context.user_data["task_desc"],
                department=context.user_data["task_dept"],
                submission_deadline=context.user_data["task_deadline"],
                total_mark_on=context.user_data["task_mark"],
                supporting_doc=doc_url,
                file_id=doc_id,
                file_name=doc_name,
                created_by=user.id,
            )
            session.add(task)

    context.user_data.clear()
    await update.message.reply_text("✅ Task created successfully!")
    return ConversationHandler.END


give_task_conv = ConversationHandler(
    entry_points=[CommandHandler("givetask", give_task_start)],
    states={
        TASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, give_task_name)],
        TASK_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, give_task_desc)],
        TASK_DEPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, give_task_dept), CommandHandler("skip", skip_task_dept)],
        TASK_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, give_task_deadline)],
        TASK_MARK: [MessageHandler(filters.TEXT & ~filters.COMMAND, give_task_mark)],
        TASK_DOC: [MessageHandler(filters.Document.ALL, give_task_doc), MessageHandler(filters.TEXT & ~filters.COMMAND, give_task_doc), CommandHandler("skip", skip_task_doc)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)


tasks_handlers = [
    submit_conv,
    give_task_conv,
]
