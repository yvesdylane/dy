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


async def _assign_todays_cleaning():
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from db.database import async_session
    from models.models import CleaningDuty, CleaningGroup, CleaningGroupMember

    today = date.today()
    if today.weekday() == 6:
        return

    async with async_session() as session:
        async with session.begin():
            exists = await session.execute(
                select(CleaningDuty).where(CleaningDuty.date == today)
            )
            if exists.scalar_one_or_none():
                return

            groups = (await session.execute(
                select(CleaningGroup)
                .options(selectinload(CleaningGroup.members))
                .order_by(CleaningGroup.turn_order)
            )).scalars().all()

            if not groups:
                return

            # Pick the next group where not all members have cycle_cleaned
            last_duty = (await session.execute(
                select(CleaningDuty).order_by(CleaningDuty.date.desc()).limit(1)
            )).scalar_one_or_none()

            start_idx = 0
            if last_duty:
                for i, g in enumerate(groups):
                    if g.id == last_duty.group_id:
                        start_idx = (i + 1) % len(groups)
                        break

            selected = None
            for offset in range(len(groups)):
                idx = (start_idx + offset) % len(groups)
                g = groups[idx]
                if any(not m.cycle_cleaned for m in g.members):
                    selected = g
                    break

            if not selected:
                # All members have cycle_cleaned — reset and use first group
                all_members = (await session.execute(
                    select(CleaningGroupMember)
                )).scalars().all()
                for m in all_members:
                    m.cycle_cleaned = False
                selected = groups[0]

            session.add(CleaningDuty(
                group_id=selected.id,
                date=today,
            ))
            logger.info("Assigned cleaning duty to %s on %s", selected.name, today)


async def _notify_cleaning_morning():
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from bot.router import application
    from db.database import async_session
    from models.models import CleaningDuty, CleaningGroupMember

    today = date.today()
    async with async_session() as session:
        duty = (await session.execute(
            select(CleaningDuty)
            .options(
                selectinload(CleaningDuty.group).selectinload(CleaningGroup.members).selectinload(CleaningGroupMember.user),
            )
            .where(CleaningDuty.date == today)
        )).scalar_one_or_none()

    if not duty or not application:
        return

    for m in duty.group.members:
        u = m.user
        if u.telegram_id and not u.telegram_id.startswith("pending_"):
            try:
                await application.bot.send_message(
                    chat_id=int(u.telegram_id),
                    text=f"🧹 Good morning! *{duty.group.name}* is on cleaning duty today. Please complete your tasks before 3:30 PM.",
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.warning("Failed to notify %s about cleaning: %s", u.telegram_id, e)


async def _notify_cleaning_afternoon():
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from bot.router import application
    from db.database import async_session
    from models.models import CleaningCompletion, CleaningDuty, CleaningGroupMember

    today = date.today()
    async with async_session() as session:
        duty = (await session.execute(
            select(CleaningDuty)
            .options(
                selectinload(CleaningDuty.group).selectinload(CleaningGroup.members).selectinload(CleaningGroupMember.user),
                selectinload(CleaningDuty.completions),
            )
            .where(CleaningDuty.date == today)
        )).scalar_one_or_none()

    if not duty or not application:
        return

    completed_user_ids = {c.user_id for c in duty.completions}
    for m in duty.group.members:
        if m.user_id in completed_user_ids:
            continue
        u = m.user
        if u.telegram_id and not u.telegram_id.startswith("pending_"):
            try:
                await application.bot.send_message(
                    chat_id=int(u.telegram_id),
                    text="⏰ Reminder: Don't forget to complete your cleaning duty today!",
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.warning("Failed to remind %s about cleaning: %s", u.telegram_id, e)


async def _auto_complete_cleaning():
    from datetime import datetime

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from db.database import async_session
    from models.models import CleaningCompletion, CleaningDuty, CleaningGroupMember

    today = date.today()
    async with async_session() as session:
        async with session.begin():
            duty = (await session.execute(
                select(CleaningDuty)
                .options(
                    selectinload(CleaningDuty.group).selectinload(CleaningGroup.members),
                    selectinload(CleaningDuty.completions),
                )
                .where(CleaningDuty.date == today)
            )).scalar_one_or_none()

            if not duty:
                return

            completed_user_ids = {c.user_id for c in duty.completions}
            now = datetime.utcnow()
            for m in duty.group.members:
                if m.user_id in completed_user_ids:
                    continue
                session.add(CleaningCompletion(
                    duty_id=duty.id,
                    user_id=m.user_id,
                    completed_at=now,
                ))
                m.cycle_cleaned = True

            duty.status = "completed"
            duty.completed_at = now
            logger.info("Auto-completed cleaning duty for %s on %s (%d members)", duty.group.name, today, len(duty.group.members))


def start_scheduler():
    scheduler.add_job(auto_create_attendance, CronTrigger(hour=7, minute=0))
    scheduler.add_job(_assign_todays_cleaning, CronTrigger(hour=6, minute=0))
    scheduler.add_job(_notify_cleaning_morning, CronTrigger(hour=9, minute=0))
    scheduler.add_job(_notify_cleaning_afternoon, CronTrigger(hour=15, minute=30))
    scheduler.add_job(_auto_complete_cleaning, CronTrigger(hour=20, minute=0))
    scheduler.start()
    logger.info("Scheduler started (attendance + cleaning)")


def stop_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler stopped")
