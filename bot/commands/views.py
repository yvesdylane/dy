import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import CommandHandler

from bot.common import format_user_info, get_user_sync, reply_fn, reply_md_fn
from bot.router import ASSETS_DIR
from config import settings

logger = logging.getLogger(__name__)


async def start(update: Update, _context):
    telegram_id = str(update.effective_user.id)
    mini_app_url = settings.mini_app_url.rstrip("/")
    button = InlineKeyboardButton("Open App", web_app=WebAppInfo(url=mini_app_url))
    keyboard = InlineKeyboardMarkup([[button]])

    try:
        await update.get_bot().set_chat_menu_button(
            menu_button={
                "type": "web_app",
                "text": "dy",
                "web_app": {"url": settings.mini_app_url.rstrip("/")},
            }
        )
    except Exception as e:
        logger.warning("Failed to set menu button: %s", e)

    logo_path = ASSETS_DIR / "logo.png"
    description = (
        "👋 *Welcome to dy!*\n\n"
        "Manage attendance, tasks, notes, and announcements for your institute.\n\n"
        "Use /me to view your profile, or open the mini app below."
    )
    try:
        if logo_path.exists():
            await update.message.reply_photo(
                photo=logo_path.read_bytes(),
                caption=description,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
        else:
            await update.message.reply_text(
                description,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
    except Exception as e:
        logger.error("Start command failed: %s", e)
        await update.message.reply_text(
            description,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )


async def me(update: Update, _context):
    telegram_id = str(update.effective_user.id)
    reply_text = reply_fn(update)
    reply_md = reply_md_fn(update)

    user = get_user_sync(telegram_id)
    if not user:
        mini_app_url = settings.mini_app_url.rstrip("/")
        button = InlineKeyboardButton("Create Account", web_app=WebAppInfo(url=mini_app_url))
        keyboard = InlineKeyboardMarkup([[button]])
        await reply_text(
            "You don't have an account yet. Tap the button below to create one.",
            reply_markup=keyboard,
        )
        return

    text = format_user_info(user)
    image_id = user.image

    if image_id:
        try:
            file = await update.effective_message.bot.get_file(image_id)
            photo_bytes = await file.download_as_bytearray()
            await update.effective_message.reply_photo(
                photo=photo_bytes,
                caption=text,
                parse_mode="Markdown",
            )
        except Exception:
            try:
                await update.effective_message.reply_document(
                    document=image_id,
                    caption=text,
                    parse_mode="Markdown",
                )
            except Exception:
                try:
                    await reply_md(text)
                except Exception:
                    await reply_text(text)
    else:
        try:
            await reply_md(text)
        except Exception:
            await reply_text(text)


async def dashboard(update: Update, _context):
    telegram_id = str(update.effective_user.id)
    mini_app_url = f"{settings.mini_app_url.rstrip('/')}?telegram_id={telegram_id}"
    button = InlineKeyboardButton("Open Dashboard", web_app=WebAppInfo(url=mini_app_url))
    keyboard = InlineKeyboardMarkup([[button]])
    await update.message.reply_text(
        "Open your dashboard below:",
        reply_markup=keyboard,
    )


async def cancel(update: Update, _context):
    await update.message.reply_text("Cancelled.")


async def skip(update: Update, _context):
    await update.message.reply_text("Skipped.")


views_handlers = [
    CommandHandler("start", start),
    CommandHandler("me", me),
    CommandHandler("dashboard", dashboard),
    CommandHandler("cancel", cancel),
    CommandHandler("skip", skip),
]
