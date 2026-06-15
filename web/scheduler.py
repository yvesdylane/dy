import logging
from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def auto_create_attendance():
    from sqlalchemy import select

    from db.database import async_session
    from models.models import Attendance, Group

    today = date.today()
    if today.weekday() == 6:
        return
    group = Group.A if today.weekday() in (0, 2, 4) else Group.B
    async with async_session() as session:
        async with session.begin():
            exists = await session.execute(
                select(Attendance).where(Attendance.date == today, Attendance.group == group)
            )
            if not exists.scalar_one_or_none():
                session.add(Attendance(date=today, group=group))
                logger.info("Auto-created attendance for %s group %s", today, group.value)


def start_scheduler():
    scheduler.add_job(auto_create_attendance, CronTrigger(hour=7, minute=0))
    scheduler.start()
    logger.info("Attendance scheduler started")


def stop_scheduler():
    scheduler.shutdown()
    logger.info("Attendance scheduler stopped")
