from sqlalchemy import select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from bot.handlers.common import get_user, logger

NOTE_TITLE, NOTE_CONTENT, NOTE_DEPT, NOTE_FILE = range(4)


async def cancel(update: Update, _context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


async def notes_list(update: Update, _context):
    from db.database import async_session
    from models.models import Note

    user = await get_user(str(update.effective_user.id))
    if not user:
        await update.effective_message.reply_text("You need an account first.")
        return

    async with async_session() as session:
        q = select(Note).order_by(Note.created_at.desc())
        if not user.role.value == "admin":
            q = q.where(Note.department == user.department)
        notes = (await session.execute(q)).scalars().all()

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
    from db.database import async_session
    from models.models import Note

    query = update.callback_query
    await query.answer()

    note_id = int(query.data.split("_")[1])
    async with async_session() as session:
        n = (await session.execute(select(Note).where(Note.id == note_id))).scalar_one_or_none()

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
            logger.error("Failed to send note file (file_id): error=%s", e)
    elif n.file_url:
        try:
            from bot.files import migrate_cloudinary_file
            result = await migrate_cloudinary_file(n.file_url, n.file_name)
            if result:
                fid, fname = result
                from db.database import async_session
                from models.models import Note
                async with async_session() as session:
                    async with session.begin():
                        obj = await session.get(Note, n.id)
                        if obj:
                            obj.file_id = fid
                            obj.file_name = fname
                await query.message.reply_document(
                    document=fid,
                    filename=fname,
                    caption=f"📎 {n.title}",
                )
        except Exception as e:
            logger.error("Failed to send note file: url=%s error=%s", n.file_url, e)
            await query.message.reply_text(f"⚠️ Could not send attachment.")
    else:
        await query.message.reply_text("ℹ️ No attachment for this note.")


async def give_note_start(update: Update, _context):
    from models.models import Role

    user = await get_user(str(update.effective_user.id))
    if not user or user.role not in (Role.admin, Role.instructor):
        await update.message.reply_text("Only admins and instructors can create notes.")
        return ConversationHandler.END

    await update.message.reply_text("Send the *note title*:")
    return NOTE_TITLE


async def give_note_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["note_title"] = update.message.text
    await update.message.reply_text(
        "Send the *content* (or send `/skip` to skip):"
    )
    return NOTE_CONTENT


async def skip_note_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["note_content"] = None
    await update.message.reply_text(
        "Send the *department* (ISM / SWE / CGWD / EDM / CSNW / DBM / CNWS / NS)\n"
        "Or send `/skip` to use your own department."
    )
    return NOTE_DEPT


async def give_note_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["note_content"] = update.message.text
    await update.message.reply_text(
        "Send the *department* (ISM / SWE / CGWD / EDM / CSNW / DBM / CNWS / NS)\n"
        "Or send `/skip` to use your own department."
    )
    return NOTE_DEPT


async def skip_note_dept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(str(update.effective_user.id))
    context.user_data["note_dept"] = user.department
    await update.message.reply_text("Upload the *file* (or send `/skip` to skip):")
    return NOTE_FILE


async def give_note_dept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from models.models import Department

    try:
        context.user_data["note_dept"] = Department(update.message.text.strip().upper())
    except ValueError:
        await update.message.reply_text("Invalid department. Try: ISM / SWE / CGWD / EDM / CSNW / DBM / CNWS / NS")
        return NOTE_DEPT

    await update.message.reply_text(
        "Upload the *file* (or send `/skip` to skip):"
    )
    return NOTE_FILE


async def skip_note_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from db.database import async_session
    from models.models import Note

    user = await get_user(str(update.effective_user.id))
    async with async_session() as session:
        async with session.begin():
            session.add(Note(
                title=context.user_data["note_title"],
                content=context.user_data["note_content"],
                department=context.user_data["note_dept"],
                file_url=None,
                uploaded_by=user.id,
            ))

    context.user_data.clear()
    await update.message.reply_text("✅ Note created successfully!")
    return ConversationHandler.END


async def give_note_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from db.database import async_session
    from models.models import Note

    user = await get_user(str(update.effective_user.id))

    file_id = None
    file_name = None
    file_url_for_legacy = None
    if update.message.document:
        file = await context.bot.get_file(update.message.document.file_id)
        file_bytes = await file.download_as_bytearray()
        from bot.files import upload_file_to_group
        file_id, file_name = await upload_file_to_group(bytes(file_bytes), update.message.document.file_name or "note")
        file_url_for_legacy = file_id

    async with async_session() as session:
        async with session.begin():
            note = Note(
                title=context.user_data["note_title"],
                content=context.user_data["note_content"],
                department=context.user_data["note_dept"],
                file_url=file_url_for_legacy,
                file_id=file_id,
                file_name=file_name,
                uploaded_by=user.id,
            )
            session.add(note)

    context.user_data.clear()
    await update.message.reply_text("✅ Note created successfully!")
    return ConversationHandler.END


give_note_conv = ConversationHandler(
    entry_points=[CommandHandler("givenotes", give_note_start)],
    states={
        NOTE_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, give_note_title)],
        NOTE_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, give_note_content), CommandHandler("skip", skip_note_content)],
        NOTE_DEPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, give_note_dept), CommandHandler("skip", skip_note_dept)],
        NOTE_FILE: [MessageHandler(filters.Document.ALL, give_note_file), MessageHandler(filters.TEXT & ~filters.COMMAND, give_note_file), CommandHandler("skip", skip_note_file)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)


notes_handlers = [
    CommandHandler("notes", notes_list),
    give_note_conv,
    CallbackQueryHandler(note_detail_callback, pattern="^note_"),
]
