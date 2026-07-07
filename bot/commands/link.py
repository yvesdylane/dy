import logging

from sqlalchemy import select
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CommandHandler, MessageHandler, filters

from bot.common import logger
from db.database import get_sync_db
from models.user import User

logger = logging.getLogger(__name__)


async def link_cmd(update: Update, _context):
    button = KeyboardButton("Share Contact", request_contact=True)
    markup = ReplyKeyboardMarkup([[button]], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "Share your phone number to link your Telegram account:",
        reply_markup=markup,
    )


async def handle_contact(update: Update, _context):
    contact = update.message.contact
    if not contact:
        return
    phone = contact.phone_number
    if not phone.startswith("+"):
        phone = "+237" + phone
    caller_id = str(update.effective_user.id)
    contact_user_id = str(contact.user_id)

    with get_sync_db() as session:
        user = session.execute(
            select(User).where(User.phone == phone)
        ).scalar_one_or_none()

        if caller_id == contact_user_id:
            if user:
                user.telegram_id = caller_id
                await update.message.reply_text(
                    f"Linked! Welcome back {user.name} {user.surname}.",
                    reply_markup=ReplyKeyboardRemove(),
                )
                return
            else:
                await update.message.reply_text(
                    "No account found with this phone number.",
                    reply_markup=ReplyKeyboardRemove(),
                )
                return

        if not user:
            await update.message.reply_text(
                "No account found with this phone number.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        if user.telegram_id and not user.telegram_id.startswith("pending_") and user.telegram_id != caller_id:
            old_tid = user.telegram_id
            user.telegram_id = caller_id
            try:
                await update.get_bot().send_message(
                    chat_id=int(old_tid),
                    text="⚠️ Your phone number has been linked to a new account. If this wasn't you, please contact support.",
                )
            except Exception:
                pass
            await update.message.reply_text(
                f"Linked! Welcome {user.name} {user.surname}.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        if user.telegram_id == caller_id:
            await update.message.reply_text(
                "Already linked!",
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        user.telegram_id = caller_id

    await update.message.reply_text(
        f"Linked! Welcome {user.name} {user.surname}.",
        reply_markup=ReplyKeyboardRemove(),
    )


link_handlers = [
    CommandHandler("link", link_cmd),
    MessageHandler(filters.CONTACT, handle_contact),
]
