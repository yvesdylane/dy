import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from models.models import (
    Attendance,
    CreationCode,
    Info,
    InternAttendance,
    Note,
    Task,
    TaskSubmission,
    User,
)

logger = logging.getLogger(__name__)

TABLES_IN_ORDER = [
    "user",
    "attendance",
    "intern_attendance",
    "task",
    "task_submission",
    "info",
    "note",
    "creation_code",
]


async def sync_database(uploaded_db_path: str) -> str:
    from db.database import async_session as main_sessionmaker

    upload_engine = create_async_engine(f"sqlite+aiosqlite:///{uploaded_db_path}")
    id_maps: dict[str, dict[int, int]] = {}
    reports: list[str] = []

    try:
        async with AsyncSession(upload_engine) as upload_session:
            users = (await upload_session.execute(select(User))).scalars().all()
            attendances = (await upload_session.execute(select(Attendance))).scalars().all()
            intern_attendances = (await upload_session.execute(select(InternAttendance))).scalars().all()
            tasks = (await upload_session.execute(select(Task))).scalars().all()
            submissions = (await upload_session.execute(select(TaskSubmission))).scalars().all()
            infos = (await upload_session.execute(select(Info))).scalars().all()
            notes = (await upload_session.execute(select(Note))).scalars().all()
            codes = (await upload_session.execute(select(CreationCode))).scalars().all()
    finally:
        await upload_engine.dispose()

    await _sync_users(main_sessionmaker, users, id_maps)
    reports.append(f"Users: {len(users)} processed")

    await _sync_attendances(main_sessionmaker, attendances, id_maps)
    reports.append(f"Attendances: {len(attendances)} processed")

    await _sync_intern_attendances(main_sessionmaker, intern_attendances, id_maps)
    reports.append(f"Intern attendances: {len(intern_attendances)} processed")

    await _sync_tasks(main_sessionmaker, tasks, id_maps)
    reports.append(f"Tasks: {len(tasks)} processed")

    await _sync_task_submissions(main_sessionmaker, submissions, id_maps)
    reports.append(f"Task submissions: {len(submissions)} processed")

    await _sync_infos(main_sessionmaker, infos, id_maps)
    reports.append(f"Infos: {len(infos)} processed")

    await _sync_notes(main_sessionmaker, notes, id_maps)
    reports.append(f"Notes: {len(notes)} processed")

    await _sync_creation_codes(main_sessionmaker, codes, id_maps)
    reports.append(f"Creation codes: {len(codes)} processed")

    return "\n".join(reports)


def _copy_fields(target, source, table, skip_columns=("id",)):
    for col in table.columns:
        if col.name in skip_columns:
            continue
        val = getattr(source, col.name)
        if isinstance(val, datetime):
            val = val.replace(tzinfo=None)
        setattr(target, col.name, val)


async def _sync_users(sessionmaker, items, id_maps):
    id_maps["user"] = {}
    async with sessionmaker() as session:
        async with session.begin():
            for item in items:
                existing = (
                    await session.execute(
                        select(User).where(User.telegram_id == item.telegram_id)
                    )
                ).scalar_one_or_none()

                if existing:
                    _copy_fields(existing, item, User.__table__, ("id", "telegram_id", "created_at"))
                    id_maps["user"][item.id] = existing.id
                else:
                    new = User(
                        name=item.name, surname=item.surname, phone=item.phone,
                        telegram_id=item.telegram_id, gender=item.gender,
                        role=item.role, department=item.department, group=item.group,
                        school=item.school, dob=item.dob, quarter=item.quarter,
                        fees_paid=item.fees_paid, total_fees=item.total_fees,
                    )
                    session.add(new)
                    await session.flush()
                    id_maps["user"][item.id] = new.id


async def _sync_attendances(sessionmaker, items, id_maps):
    id_maps["attendance"] = {}
    async with sessionmaker() as session:
        async with session.begin():
            for item in items:
                existing = (
                    await session.execute(
                        select(Attendance).where(
                            Attendance.date == item.date,
                            Attendance.group == item.group,
                        )
                    )
                ).scalar_one_or_none()

                if existing:
                    id_maps["attendance"][item.id] = existing.id
                else:
                    new = Attendance(date=item.date, group=item.group)
                    session.add(new)
                    await session.flush()
                    id_maps["attendance"][item.id] = new.id


async def _sync_intern_attendances(sessionmaker, items, id_maps):
    async with sessionmaker() as session:
        async with session.begin():
            for item in items:
                mapped_attendance_id = id_maps.get("attendance", {}).get(item.attendance_id)
                mapped_user_id = id_maps.get("user", {}).get(item.user_id)
                if not mapped_attendance_id or not mapped_user_id:
                    logger.warning(
                        "Skipping intern_attendance: attendance %s or user %s not mapped",
                        item.attendance_id, item.user_id,
                    )
                    continue

                existing = (
                    await session.execute(
                        select(InternAttendance).where(
                            InternAttendance.attendance_id == mapped_attendance_id,
                            InternAttendance.user_id == mapped_user_id,
                        )
                    )
                ).scalar_one_or_none()

                if existing:
                    existing.enter_at = item.enter_at
                    existing.left_at = item.left_at
                else:
                    session.add(
                        InternAttendance(
                            attendance_id=mapped_attendance_id,
                            user_id=mapped_user_id,
                            enter_at=item.enter_at,
                            left_at=item.left_at,
                        )
                    )


async def _sync_tasks(sessionmaker, items, id_maps):
    id_maps["task"] = {}
    async with sessionmaker() as session:
        async with session.begin():
            for item in items:
                mapped_creator_id = id_maps.get("user", {}).get(item.created_by)
                if not mapped_creator_id:
                    logger.warning("Skipping task %s: creator %s not mapped", item.id, item.created_by)
                    continue

                existing = (
                    await session.execute(
                        select(Task).where(
                            Task.name == item.name,
                            Task.department == item.department,
                            Task.submission_deadline == item.submission_deadline,
                        )
                    )
                ).scalar_one_or_none()

                if existing:
                    _copy_fields(existing, item, Task.__table__, ("id", "created_at"))
                    existing.created_by = mapped_creator_id
                    id_maps["task"][item.id] = existing.id
                else:
                    new = Task(
                        name=item.name, description=item.description,
                        supporting_doc=item.supporting_doc, department=item.department,
                        submission_deadline=item.submission_deadline,
                        total_mark_on=item.total_mark_on, created_by=mapped_creator_id,
                    )
                    session.add(new)
                    await session.flush()
                    id_maps["task"][item.id] = new.id


async def _sync_task_submissions(sessionmaker, items, id_maps):
    async with sessionmaker() as session:
        async with session.begin():
            for item in items:
                mapped_task_id = id_maps.get("task", {}).get(item.task_id)
                mapped_user_id = id_maps.get("user", {}).get(item.user_id)
                if not mapped_task_id or not mapped_user_id:
                    logger.warning(
                        "Skipping submission %s: task %s or user %s not mapped",
                        item.id, item.task_id, item.user_id,
                    )
                    continue

                existing = (
                    await session.execute(
                        select(TaskSubmission).where(
                            TaskSubmission.task_id == mapped_task_id,
                            TaskSubmission.user_id == mapped_user_id,
                        )
                    )
                ).scalar_one_or_none()

                if existing:
                    _copy_fields(existing, item, TaskSubmission.__table__, ("id",))
                    existing.task_id = mapped_task_id
                    existing.user_id = mapped_user_id
                else:
                    new = TaskSubmission(
                        task_id=mapped_task_id, user_id=mapped_user_id,
                        submitted_file=item.submitted_file,
                        submitted_at=item.submitted_at,
                        mark_obtained=item.mark_obtained, feedback=item.feedback,
                    )
                    session.add(new)


async def _sync_infos(sessionmaker, items, id_maps):
    async with sessionmaker() as session:
        async with session.begin():
            for item in items:
                mapped_creator_id = id_maps.get("user", {}).get(item.created_by)
                if not mapped_creator_id:
                    logger.warning("Skipping info %s: creator %s not mapped", item.id, item.created_by)
                    continue

                existing = (
                    await session.execute(
                        select(Info).where(
                            Info.title == item.title,
                            Info.created_at == item.created_at,
                        )
                    )
                ).scalar_one_or_none()

                if existing:
                    _copy_fields(existing, item, Info.__table__, ("id", "created_at"))
                    existing.created_by = mapped_creator_id
                else:
                    new = Info(
                        title=item.title, content=item.content,
                        file_url=item.file_url, created_by=mapped_creator_id,
                    )
                    session.add(new)


async def _sync_notes(sessionmaker, items, id_maps):
    async with sessionmaker() as session:
        async with session.begin():
            for item in items:
                mapped_uploader_id = id_maps.get("user", {}).get(item.uploaded_by)
                if not mapped_uploader_id:
                    logger.warning("Skipping note %s: uploader %s not mapped", item.id, item.uploaded_by)
                    continue

                existing = (
                    await session.execute(
                        select(Note).where(
                            Note.title == item.title,
                            Note.department == item.department,
                            Note.created_at == item.created_at,
                        )
                    )
                ).scalar_one_or_none()

                if existing:
                    _copy_fields(existing, item, Note.__table__, ("id", "created_at"))
                    existing.uploaded_by = mapped_uploader_id
                else:
                    new = Note(
                        title=item.title, content=item.content,
                        file_url=item.file_url, department=item.department,
                        uploaded_by=mapped_uploader_id,
                    )
                    session.add(new)


async def _sync_creation_codes(sessionmaker, items, id_maps):
    async with sessionmaker() as session:
        async with session.begin():
            for item in items:
                mapped_creator_id = id_maps.get("user", {}).get(item.created_by)
                if not mapped_creator_id:
                    logger.warning("Skipping code %s: creator %s not mapped", item.id, item.created_by)
                    continue

                existing = (
                    await session.execute(
                        select(CreationCode).where(CreationCode.code == item.code)
                    )
                ).scalar_one_or_none()

                if existing:
                    _copy_fields(existing, item, CreationCode.__table__, ("id", "created_at"))
                    existing.created_by = mapped_creator_id
                else:
                    new = CreationCode(
                        code=item.code, role=item.role,
                        expires_at=item.expires_at, is_used=item.is_used,
                        created_by=mapped_creator_id,
                    )
                    session.add(new)
