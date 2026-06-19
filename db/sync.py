import logging
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.types import Date, DateTime, Numeric

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


async def _fetch_all(upload_session, model, table_name):
    try:
        return (await upload_session.execute(select(model))).scalars().all()
    except Exception:
        rows = (await upload_session.execute(text(f"SELECT * FROM {table_name}"))).all()
        col_names = list(rows[0]._mapping.keys()) if rows else []
        items = []
        for row in rows:
            item = model()
            for col in model.__table__.columns:
                if col.name not in col_names:
                    continue
                val = row._mapping[col.name]
                if isinstance(col.type, DateTime) and isinstance(val, str):
                    from datetime import datetime as _dt
                    val = _dt.strptime(val, "%Y-%m-%d %H:%M:%S.%f")
                elif isinstance(col.type, Date) and isinstance(val, str):
                    from datetime import datetime as _dt
                    val = _dt.strptime(val, "%Y-%m-%d").date()
                elif isinstance(col.type, Numeric) and isinstance(val, (int, float)):
                    from decimal import Decimal
                    val = Decimal(str(val))
                setattr(item, col.name, val)
            items.append(item)
        return items


async def sync_database(uploaded_db_path: str) -> str:
    from db.database import async_session as main_sessionmaker

    upload_engine = create_async_engine(f"sqlite+aiosqlite:///{uploaded_db_path}")
    id_maps: dict[str, dict[int, int]] = {}
    reports: list[str] = []

    try:
        async with AsyncSession(upload_engine) as upload_session:
            users = await _fetch_all(upload_session, User, "users")
            attendances = await _fetch_all(upload_session, Attendance, "attendances")
            intern_attendances = await _fetch_all(upload_session, InternAttendance, "intern_attendances")
            tasks = await _fetch_all(upload_session, Task, "tasks")
            submissions = await _fetch_all(upload_session, TaskSubmission, "task_submissions")
            infos = await _fetch_all(upload_session, Info, "infos")
            notes = await _fetch_all(upload_session, Note, "notes")
            codes = await _fetch_all(upload_session, CreationCode, "creation_codes")
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

    migrated = await _migrate_user_images(main_sessionmaker, users)
    if migrated:
        reports.append(f"Profile images migrated: {migrated}")

    return "\n".join(reports)


def _copy_fields(target, source, table, skip_columns=("id",)):
    for col in table.columns:
        if col.name in skip_columns:
            continue
        val = getattr(source, col.name)
        if isinstance(val, datetime):
            val = val.replace(tzinfo=None)
        setattr(target, col.name, val)


async def _migrate_user_images(sessionmaker, users):
    from bot.files import migrate_cloudinary_file, upload_file_to_group
    from bot.router import application

    bot = application.bot
    migrated = 0
    async with sessionmaker() as session:
        async with session.begin():
            for item in users:
                if not item.image:
                    continue
                existing = (
                    await session.execute(
                        select(User).where(User.telegram_id == item.telegram_id)
                    )
                ).scalar_one_or_none()
                if not existing:
                    continue
                if existing.image == item.image:
                    continue
                try:
                    if item.image.startswith("http"):
                        result = await migrate_cloudinary_file(item.image, f"profile_{item.telegram_id}.jpg")
                        if result:
                            fid, _ = result
                            existing.image = fid
                            migrated += 1
                    else:
                        tg_file = await bot.get_file(item.image)
                        file_bytes = await tg_file.download_as_bytearray()
                        fid, _ = await upload_file_to_group(bytes(file_bytes), f"profile_{item.telegram_id}.jpg")
                        existing.image = fid
                        migrated += 1
                except Exception as e:
                    logger.error("Failed to migrate image for user %s: %s", item.telegram_id, e)
    return migrated


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
                        image=item.image,
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
                        file_id=getattr(item, "file_id", None),
                        file_name=getattr(item, "file_name", None),
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
                        file_id=getattr(item, "file_id", None),
                        file_name=getattr(item, "file_name", None),
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
                        file_url=item.file_url,
                        file_id=getattr(item, "file_id", None),
                        file_name=getattr(item, "file_name", None),
                        created_by=mapped_creator_id,
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
                        file_url=item.file_url,
                        file_id=getattr(item, "file_id", None),
                        file_name=getattr(item, "file_name", None),
                        department=item.department,
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
