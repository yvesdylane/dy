import logging

from sqlalchemy import select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler

from bot.common import INACTIVE_MSG, get_user_sync, reply_fn
from db.database import get_sync_db
from models.enums import Role
from models.infoNote import Info, Note
from models.task import Task

logger = logging.getLogger(__name__)


async def announcements(update: Update, _context):
    user = get_user_sync(str(update.effective_user.id))
    if user and not user.is_active:
        await update.effective_message.reply_text(INACTIVE_MSG)
        return

    with get_sync_db() as session:
        items = session.execute(
            select(Info).order_by(Info.created_at.desc())
        ).scalars().all()

    if not items:
        await update.effective_message.reply_text("No announcements yet.")
        return

    btns = [InlineKeyboardButton(item.title[:40], callback_data=f"info_{item.id}") for item in items]
    keyboard = [btns[i:i+2] for i in range(0, len(btns), 2)]
    await update.effective_message.reply_text(
        "📢 *Announcements:*\nSelect one to view details.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def info_detail_callback(update: Update, _context):
    query = update.callback_query
    await query.answer()
    info_id = int(query.data.split("_")[1])

    with get_sync_db() as session:
        item = session.execute(select(Info).where(Info.id == info_id)).scalar_one_or_none()

    if not item:
        await query.message.reply_text("Announcement not found.")
        return

    text = f"*{item.title}*\n_{item.created_at.date()}_\n\n{item.content}"
    await query.message.reply_markdown(text)

    if item.file_id:
        try:
            await query.message.reply_document(
                document=item.file_id,
                filename=item.file_name or item.file_id,
                caption=f"📎 {item.title}",
            )
        except Exception as e:
            logger.error("Failed to send info file: %s", e)
    elif item.file_url:
        try:
            await query.message.reply_document(
                document=item.file_url,
                filename=item.file_name or "attachment",
                caption=f"📎 {item.title}",
            )
        except Exception as e:
            logger.error("Failed to send info file via URL: %s", e)


async def notes_list(update: Update, _context):
    user = get_user_sync(str(update.effective_user.id))
    if not user:
        await update.effective_message.reply_text("You need an account first.")
        return
    if not user.is_active:
        await update.effective_message.reply_text(INACTIVE_MSG)
        return

    with get_sync_db() as session:
        q = select(Note).order_by(Note.created_at.desc())
        if user.role != Role.admin:
            q = q.where(Note.department == user.department)
        notes = session.execute(q).scalars().all()

    if not notes:
        await update.effective_message.reply_text("No notes found.")
        return

    btns = [InlineKeyboardButton(n.title, callback_data=f"note_{n.id}") for n in notes]
    keyboard = [btns[i:i+2] for i in range(0, len(btns), 2)]
    await update.effective_message.reply_text(
        "Select a note:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def note_detail_callback(update: Update, _context):
    query = update.callback_query
    await query.answer()

    note_id = int(query.data.split("_")[1])
    with get_sync_db() as session:
        n = session.execute(select(Note).where(Note.id == note_id)).scalar_one_or_none()

    if not n:
        await query.message.reply_text("Note not found.")
        return

    lines = [f"*{n.title}*", f"_{n.created_at.date()}_"]
    if n.content:
        lines.append(f"\n📝 {n.content}")
    await query.message.reply_markdown("\n".join(lines))

    if n.file_id:
        try:
            await query.message.reply_document(
                document=n.file_id,
                filename=n.file_name or n.file_id,
                caption=f"📎 {n.title}",
            )
        except Exception as e:
            logger.error("Failed to send note file: %s", e)
    elif n.file_url:
        try:
            await query.message.reply_document(
                document=n.file_url,
                filename=n.file_name or "attachment",
                caption=f"📎 {n.title}",
            )
        except Exception as e:
            logger.error("Failed to send note file via URL: %s", e)


async def task_info(update: Update, _context):
    reply = reply_fn(update)

    user = get_user_sync(str(update.effective_user.id))
    if not user:
        await reply("You need an account first.")
        return
    if not user.is_active:
        await reply(INACTIVE_MSG)
        return

    from datetime import datetime

    with get_sync_db() as session:
        q = select(Task).where(Task.submission_deadline >= datetime.utcnow())
        if user.role == Role.intern:
            q = q.where(Task.department == user.department)
        q = q.order_by(Task.submission_deadline)
        tasks = session.execute(q).scalars().all()

    if not tasks:
        await reply("No active tasks found.")
        return

    btns = [InlineKeyboardButton(t.name, callback_data=f"task_{t.id}") for t in tasks]
    keyboard = [btns[i:i+2] for i in range(0, len(btns), 2)]
    scope = f"department *{user.department.value}*" if user.role == Role.intern else "all departments"
    await reply(
        f"*Active tasks ({scope}):*",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def task_detail_callback(update: Update, _context):
    query = update.callback_query
    await query.answer()

    task_id = int(query.data.split("_")[1])
    with get_sync_db() as session:
        t = session.execute(select(Task).where(Task.id == task_id)).scalar_one_or_none()

    if not t:
        await query.message.reply_text("Task not found or has been removed.")
        return

    lines = [
        f"*{t.name}*",
        f"📝 *Description:* {t.description}",
        f"📅 *Deadline:* {t.submission_deadline.strftime('%Y-%m-%d %H:%M')}",
        f"🎯 *Total Mark:* {t.total_mark_on}",
    ]
    await query.message.reply_markdown("\n".join(lines))

    if t.file_id:
        try:
            await query.message.reply_document(
                document=t.file_id,
                filename=t.file_name or t.file_id,
                caption="📎 Supporting document",
            )
        except Exception as e:
            logger.error("Failed to send supporting doc: %s", e)
    elif t.supporting_doc:
        try:
            await query.message.reply_document(
                document=t.supporting_doc,
                filename=t.file_name or "supporting_doc",
                caption="📎 Supporting document",
            )
        except Exception as e:
            logger.error("Failed to send supporting doc via URL: %s", e)


info_handlers = [
    CommandHandler("info", announcements),
    CommandHandler("notes", notes_list),
    CommandHandler("taskinfo", task_info),
    CallbackQueryHandler(info_detail_callback, pattern=r"^info_\d+$"),
    CallbackQueryHandler(note_detail_callback, pattern=r"^note_\d+$"),
    CallbackQueryHandler(task_detail_callback, pattern=r"^task_\d+$"),
]
