import logging
import warnings
from pathlib import Path

from telegram import BotCommand, BotCommandScopeAllPrivateChats, Update
from telegram.ext import Application

warnings.filterwarnings("ignore", message="If 'per_message=False', 'CallbackQueryHandler' will not be tracked")

logger = logging.getLogger(__name__)

from config import settings

logger = logging.getLogger(__name__)

application: Application | None = None
ASSETS_DIR = Path(__file__).parent.parent / "assets"


async def init_bot(handler_list: list):
    global application

    try:
        application = Application.builder().token(settings.bot_token).build()
        await application.initialize()
        await application.start()

        for handler in handler_list:
            application.add_handler(handler)

        if settings.mini_app_url:
            base_url = settings.mini_app_url.rstrip("/")
            webhook_url = f"{base_url}/telegram"
            await application.bot.set_webhook(url=webhook_url)
            logger.info("Webhook set to %s", webhook_url)

            await application.bot.set_chat_menu_button(
                menu_button={
                    "type": "web_app",
                    "text": "dy",
                    "web_app": {"url": base_url},
                }
            )
            logger.info("Mini app menu button set")

            await application.bot.set_my_commands(
                [
                    BotCommand("start", "Welcome and bot info"),
                    BotCommand("me", "View your profile"),
                    BotCommand("info", "View announcements"),
                    BotCommand("notes", "Browse notes"),
                    BotCommand("taskinfo", "Browse active tasks"),
                    BotCommand("dashboard", "Open mini app dashboard"),
                    BotCommand("link", "Link your phone number"),
                    BotCommand("image", "Set your profile picture"),
                    BotCommand("complain", "Submit anonymous complaint or advice"),
                    BotCommand("leave", "Apply for leave or review requests"),
                    BotCommand("update", "Update your name, surname or gender"),
                    BotCommand("submit", "Submit your task work"),
                    BotCommand("cancel", "Cancel current operation"),
                    BotCommand("skip", "Skip current step"),
                    BotCommand("db", "Download database backup (admin)"),
                    BotCommand("sync", "Sync from uploaded database file (admin)"),
                    BotCommand("eval", "View your daily evaluation"),
                    BotCommand("pics", "Download all profile pictures as archive (staff)"),
                ],
                scope=BotCommandScopeAllPrivateChats(),
            )
            logger.info("Bot commands set")
        else:
            logger.info("Mini app URL not set — skipping webhook and menu button registration")

        logger.info("Telegram bot initialized")
    except Exception as e:
        logger.error("Failed to initialize Telegram bot: %s", e)
        logger.warning("Web server will continue without bot — Telegram commands and webhook will be unavailable")


async def process_update(data: dict):
    if application is None:
        logger.warning("Bot not initialized, dropping update")
        return

    logger.debug("Processing Telegram update from user_id=%s",
                 data.get("message", {}).get("from", {}).get("id", "unknown"))

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
