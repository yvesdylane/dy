from sqlalchemy import select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from bot.handlers.common import get_user, reply_fn, logger

IMAGE_PHOTO = 0
COMPLAIN_TYPE, COMPLAIN_CONTENT = range(2)
UPDATE_SELECT, UPDATE_VALUE = range(2)


async def cancel(update: Update, _context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ── /image ─────────────────────────────────────────────────────────


async def image_start(update: Update, _context):
    reply = reply_fn(update)
    await reply("Send me a photo to set as your profile picture.")
    return IMAGE_PHOTO


async def image_handle_photo(update: Update, context):
    from bot.files import upload_file_to_group

    telegram_id = str(update.effective_user.id)
    reply = reply_fn(update)

    user = await get_user(telegram_id)
    if not user:
        await reply("You need an account first. Use /start to create one.")
        return ConversationHandler.END

    photo = update.message.photo[-1]
    file = await photo.get_file()
    photo_bytes = await file.download_as_bytearray()

    file_id, _ = await upload_file_to_group(
        bytes(photo_bytes),
        f"profile_{telegram_id}.jpg",
    )

    from db.database import async_session
    from models.models import User as UserModel

    async with async_session() as session:
        async with session.begin():
            u = (await session.execute(select(UserModel).where(UserModel.telegram_id == telegram_id))).scalar_one_or_none()
            if u:
                u.image = file_id

    await reply("Profile picture updated!")
    return ConversationHandler.END


image_conv = ConversationHandler(
    entry_points=[CommandHandler("image", image_start)],
    states={
        IMAGE_PHOTO: [MessageHandler(filters.PHOTO, image_handle_photo)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)


# ── /complain ──────────────────────────────────────────────────────


async def complain_start(update: Update, _context):
    from models.models import Role
    user = await get_user(str(update.effective_user.id))
    if not user:
        await update.message.reply_text("User not found.")
        return ConversationHandler.END
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💢 Complaint", callback_data="complain_type_complaint")],
        [InlineKeyboardButton("💡 Advice", callback_data="complain_type_advice")],
    ])
    await update.message.reply_text(
        "What would you like to share? (Your identity will remain anonymous — "
        "we only see your department/group)",
        reply_markup=keyboard,
    )
    return COMPLAIN_TYPE


async def complain_type_chosen(update: Update, context):
    query = update.callback_query
    await query.answer()
    ctype = query.data.split("_")[-1]
    context.user_data["complain_type"] = ctype
    await query.message.reply_text(
        f"Great, describe your {ctype} below. (Send /cancel to cancel)"
    )
    return COMPLAIN_CONTENT


async def complain_content(update: Update, context):
    content = update.message.text
    ctype = context.user_data.get("complain_type")
    if not ctype:
        await update.message.reply_text("Something went wrong. Use /complain to start over.")
        return ConversationHandler.END

    user = await get_user(str(update.effective_user.id))
    if not user:
        await update.message.reply_text("User not found.")
        return ConversationHandler.END

    from db.database import async_session
    from models.models import ComplainType, UserComplain

    async with async_session() as session:
        async with session.begin():
            c = UserComplain(
                content=content,
                complain_type=ComplainType.complaint if ctype == "complaint" else ComplainType.advice,
                department=user.department,
                group=user.group,
            )
            session.add(c)

    await update.message.reply_text(
        f"✅ Your anonymous {ctype} has been submitted. Thank you for your feedback!"
    )
    context.user_data.pop("complain_type", None)
    return ConversationHandler.END


complain_conv = ConversationHandler(
    entry_points=[CommandHandler("complain", complain_start)],
    states={
        COMPLAIN_TYPE: [CallbackQueryHandler(complain_type_chosen, pattern="^complain_type_")],
        COMPLAIN_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, complain_content)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)


# ── /update ────────────────────────────────────────────────────────


async def _show_update_menu(update: Update, context, text="What would you like to update?"):
    keyboard = [
        [InlineKeyboardButton("Name", callback_data="update_name"),
         InlineKeyboardButton("Surname", callback_data="update_surname")],
        [InlineKeyboardButton("Gender", callback_data="update_gender")],
        [InlineKeyboardButton("Done", callback_data="update_done")],
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return UPDATE_SELECT


async def update_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(str(update.effective_user.id))
    if not user:
        await update.message.reply_text("User not found.")
        return ConversationHandler.END
    return await _show_update_menu(update, context)


async def update_field_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    field = query.data.replace("update_", "")
    if field == "done":
        await query.edit_message_text("Done!")
        return ConversationHandler.END

    context.user_data["update_field"] = field
    labels = {"name": "Name", "surname": "Surname", "gender": "Gender (male/female)"}
    await query.edit_message_text(f"Enter your new {labels.get(field, field)}:")
    return UPDATE_VALUE


async def update_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import Gender, User

    field = context.user_data.get("update_field")
    if not field:
        await update.message.reply_text("Session expired. Use /update to start over.")
        return ConversationHandler.END

    value = update.message.text.strip()
    tid = str(update.effective_user.id)

    async with async_session() as session:
        async with session.begin():
            user = (await session.execute(
                select(User).where(User.telegram_id == tid)
            )).scalar_one_or_none()
            if not user:
                await update.message.reply_text("User not found.")
                return ConversationHandler.END

            if field == "name":
                user.name = value
            elif field == "surname":
                user.surname = value
            elif field == "gender":
                try:
                    user.gender = Gender(value.lower())
                except ValueError:
                    await update.message.reply_text("Invalid gender. Use 'male' or 'female'.")
                    return UPDATE_VALUE

    await update.message.reply_text(f"✅ {field.capitalize()} updated!")
    return await _show_update_menu(update, context, "Anything else?")


async def update_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Done!")
    return ConversationHandler.END


update_conv = ConversationHandler(
    entry_points=[CommandHandler("update", update_start)],
    states={
        UPDATE_SELECT: [CallbackQueryHandler(update_field_callback, pattern=r"^update_")],
        UPDATE_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_value)],
    },
    fallbacks=[CommandHandler("cancel", update_done)],
)


profile_handlers = [
    image_conv,
    complain_conv,
    update_conv,
]
