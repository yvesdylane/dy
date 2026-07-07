import asyncio
import logging

from sqlalchemy import select

from db.database import SyncSession
from models.attendance import Attendance
from models.enums import Group

logger = logging.getLogger(__name__)


async def auto_create_attendance():
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _sync_create_attendance)


def _sync_create_attendance():
    from datetime import date

    today = date.today()
    if today.weekday() == 6:
        return

    group = Group.A if today.weekday() in (0, 2, 4) else Group.B

    session = SyncSession()
    try:
        exists = session.execute(
            select(Attendance).where(Attendance.date == today, Attendance.group == group)
        ).scalar_one_or_none()
        if not exists:
            session.add(Attendance(date=today, group=group))
            session.commit()
            logger.info("Auto-created attendance for %s group %s", today, group.value)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
