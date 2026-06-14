import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import Application, CommandHandler

from bot.handlers import handlers as other_handlers
from config import settings

logger = logging.getLogger(__name__)

application: Application | None = None


async def start(update: Update, _context):
    telegram_id = str(update.effective_user.id)
    mini_app_url = f"{settings.mini_app_url.rstrip('/')}/app?telegram_id={telegram_id}"
    button = InlineKeyboardButton("Open Dashboard", web_app=WebAppInfo(url=mini_app_url))
    keyboard = InlineKeyboardMarkup([[button]])
    await update.message.reply_text("Welcome! Open your dashboard:", reply_markup=keyboard)


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
                    "text": "Open App",
                    "web_app": {"url": f"{base_url}/app"},
                }
            )
            logger.info("Mini app menu button set")
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
