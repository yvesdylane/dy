import logging

from telegram import Update
from telegram.ext import Application, CommandHandler

from bot.handlers import handlers as other_handlers
from config import settings

logger = logging.getLogger(__name__)

application: Application | None = None


async def start(update: Update, _context):
    await update.message.reply_text("Hello! I'm the dy bot.")


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
            webhook_url = f"{settings.mini_app_url.rstrip('/')}/telegram"
            await application.bot.set_webhook(url=webhook_url)
            logger.info("Webhook set to %s", webhook_url)
        else:
            logger.info("Mini app URL not set — skipping webhook registration")

        logger.info("Telegram bot initialized")
    except Exception as e:
        logger.error("Failed to initialize Telegram bot: %s", e)


async def process_update(data: dict):
    if application is None:
        logger.warning("Bot not initialized, dropping update")
        return

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
