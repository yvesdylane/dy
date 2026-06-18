import logging

from pathlib import Path

from telegram import BotCommand, BotCommandScopeAllPrivateChats, InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import Application, CommandHandler

from bot.handlers import handlers as other_handlers
from config import settings

logger = logging.getLogger(__name__)

application: Application | None = None
ASSETS_DIR = Path(__file__).parent.parent / "assets"


async def start(update: Update, _context):
    telegram_id = str(update.effective_user.id)
    mini_app_url = f"{settings.mini_app_url.rstrip('/')}/app?telegram_id={telegram_id}"
    button = InlineKeyboardButton("Open App", web_app=WebAppInfo(url=mini_app_url))
    keyboard = InlineKeyboardMarkup([[button]])
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


async def init_bot():
    global application

    try:
        application = Application.builder().token(settings.telegram_token).build()
        await application.initialize()
        await application.start()

        application.add_handler(CommandHandler("start", start))
        for handler in other_handlers:
            application.add_handler(handler)

        if settings.mini_app_url and settings.mini_app_url != "not_yet_there":
            base_url = settings.mini_app_url.rstrip("/")
            webhook_url = f"{base_url}/telegram"
            await application.bot.set_webhook(url=webhook_url)
            logger.info("Webhook set to %s", webhook_url)

            await application.bot.set_chat_menu_button(
                menu_button={
                    "type": "web_app",
                    "text": "dy",
                    "web_app": {"url": f"{base_url}/app"},
                }
            )
            logger.info("Mini app menu button set")

            await application.bot.set_my_commands(
                [
                    BotCommand("start", "Welcome and bot info"),
                    BotCommand("me", "View your profile"),
                    BotCommand("info", "View announcements"),
                    BotCommand("helpinfo", "Explore info commands"),
                    BotCommand("userinfo", "User overview"),
                    BotCommand("taskinfo", "Browse active tasks"),
                    BotCommand("givetask", "Create a new task (staff only)"),
                    BotCommand("submit", "Submit your task work"),
                    BotCommand("notes", "Browse notes"),
                    BotCommand("givenotes", "Create a new note (staff only)"),
                    BotCommand("sync", "Upload & sync database (admin only)"),
                    BotCommand("dashboard", "Open mini app dashboard"),
                    BotCommand("link", "Link your phone number"),
                    BotCommand("qr", "Generate attendance QR (staff only)"),
                    BotCommand("db", "Download database backup (admin only)"),
                    BotCommand("image", "Set your profile picture"),
                    BotCommand("cancel", "Cancel current operation"),
                    BotCommand("skip", "Skip current step"),
                ],
                scope=BotCommandScopeAllPrivateChats(),
            )
            logger.info("Bot commands set")
        else:
            logger.info("Mini app URL not set — skipping webhook and menu button registration")

        logger.info("Telegram bot initialized")
    except Exception as e:
        logger.error("Failed to initialize Telegram bot: %s", e)


async def process_update(data: dict):
    if application is None:
        logger.warning("Bot not initialized, dropping update")
        return

    logger.info("=== INCOMING TELEGRAM UPDATE ===")
    import json
    for line in json.dumps(data, indent=2, default=str).splitlines():
        logger.info("TG: %s", line)
    logger.info("=== END UPDATE ===")

    try:
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
    except Exception as e:
        logger.error("Failed to process Telegram update: %s", e)


async def shutdown_bot():
    global application
    if application:
        try:
            await application.stop()
            await application.shutdown()
            logger.info("Telegram bot shut down")
        except Exception as e:
            logger.error("Bot shutdown error: %s", e)
