import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from cronjobs.attendance import auto_create_attendance
from cronjobs.backup import backup_db
from cronjobs.evaluations import eval_start_reminder, eval_summary
from cronjobs.fees import fee_reminder

logger = logging.getLogger(__name__)

# Server is UTC, user is GMT+1 — CronTrigger times are set in Africa/Douala (GMT+1, no DST)
_tz = ZoneInfo("Africa/Douala")

scheduler = AsyncIOScheduler()
_bot = None


def get_bot():
    return _bot


def start_scheduler(bot):
    global _bot
    _bot = bot

    scheduler.add_job(
        auto_create_attendance,
        CronTrigger(hour=8, minute=0, timezone=_tz),   # 08:00 local
    )
    scheduler.add_job(
        fee_reminder,
        CronTrigger(hour=9, minute=0, timezone=_tz),    # 09:00 local
    )
    scheduler.add_job(
        eval_start_reminder,
        CronTrigger(hour=7, minute=0, timezone=_tz),    # 07:00 local
    )
    scheduler.add_job(
        backup_db,
        CronTrigger(hour=23, minute=0, timezone=_tz),   # 23:00 local
    )
    scheduler.add_job(
        eval_summary,
        CronTrigger(hour=22, minute=0, timezone=_tz),   # 22:00 local
    )
    scheduler.start()
    logger.info("Scheduler started (attendance, fees, eval reminders, backup, eval summary)")


def stop_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler stopped")
