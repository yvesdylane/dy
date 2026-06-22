import logging
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.types import Date, DateTime, Numeric

from models.models import (
    Attendance,
    CleaningCompletion,
    CleaningDuty,
    CleaningGroup,
    CleaningGroupMember,
    CreationCode,
    Info,
    InternAttendance,
    LeaveRequest,
    Note,
    Task,
    TaskSubmission,
    User,
    UserComplain,
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
            try:
                user_complains = await _fetch_all(upload_session, UserComplain, "user_complains")
            except Exception:
                user_complains = []
            try:
                leave_requests = await _fetch_all(upload_session, LeaveRequest, "leave_requests")
            except Exception:
                leave_requests = []
            try:
                cleaning_groups = await _fetch_all(upload_session, CleaningGroup, "cleaning_groups")
            except Exception:
                cleaning_groups = []
            try:
                cleaning_members = await _fetch_all(upload_session, CleaningGroupMember, "cleaning_group_members")
            except Exception:
                cleaning_members = []
            try:
                cleaning_duties = await _fetch_all(upload_session, CleaningDuty, "cleaning_duties")
            except Exception:
                cleaning_duties = []
            try:
                cleaning_completions = await _fetch_all(upload_session, CleaningCompletion, "cleaning_completions")
            except Exception:
                cleaning_completions = []
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

    if user_complains:
        await _sync_user_complains(main_sessionmaker, user_complains)
        reports.append(f"Complaints: {len(user_complains)} processed")

    if leave_requests:
        await _sync_leave_requests(main_sessionmaker, leave_requests, id_maps)
        reports.append(f"Leave requests: {len(leave_requests)} processed")

    if cleaning_groups:
        await _sync_cleaning_groups(main_sessionmaker, cleaning_groups)
        reports.append(f"Cleaning groups: {len(cleaning_groups)} processed")
    if cleaning_members:
        await _sync_cleaning_members(main_sessionmaker, cleaning_members)
        reports.append(f"Cleaning members: {len(cleaning_members)} processed")
    if cleaning_duties:
        await _sync_cleaning_duties(main_sessionmaker, cleaning_duties)
        reports.append(f"Cleaning duties: {len(cleaning_duties)} processed")
    if cleaning_completions:
        await _sync_cleaning_completions(main_sessionmaker, cleaning_completions)
        reports.append(f"Cleaning completions: {len(cleaning_completions)} processed")

    counts = await _migrate_all_files(main_sessionmaker, users, tasks, submissions, infos, notes, id_maps)
    for label, n in counts.items():
        if n:
            reports.append(f"Files migrated — {label}: {n}")

    return "\n".join(reports)


def _copy_fields(target, source, table, skip_columns=("id",)):
    for col in table.columns:
        if col.name in skip_columns:
            continue
        val = getattr(source, col.name)
        if isinstance(val, datetime):
            val = val.replace(tzinfo=None)
        setattr(target, col.name, val)


async def _migrate_all_files(sessionmaker, users, tasks, submissions, infos, notes, id_maps):
    from bot.files import migrate_cloudinary_file, upload_file_to_group
    from bot.router import application

    bot = application.bot
    counts = {"users": 0, "tasks": 0, "submissions": 0, "infos": 0, "notes": 0}

    async def _migrate_one(val, hint):
        if not val:
            return None, None
        if not val.startswith("http"):
            return val, None
        try:
            return await migrate_cloudinary_file(val, hint) or (None, None)
        except Exception as e:
            logger.error("File migration failed: %s err=%s", val, e)
            return None, None

    async with sessionmaker() as session:
        async with session.begin():
            for item in users:
                if not item.image:
                    continue
                fid, _ = await _migrate_one(item.image, f"profile_{item.telegram_id}.jpg")
                if not fid:
                    continue
                u = (await session.execute(
                    select(User).where(User.telegram_id == item.telegram_id)
                )).scalar_one_or_none()
                if u:
                    u.image = fid
                    counts["users"] += 1

            for item in tasks:
                val = getattr(item, "file_id", None) or getattr(item, "supporting_doc", None)
                if not val:
                    continue
                fid, fn = await _migrate_one(val, getattr(item, "file_name", None) or f"task_{item.id}")
                if not fid:
                    continue
                t = (await session.execute(
                    select(Task).where(
                        Task.name == item.name,
                        Task.department == item.department,
                        Task.submission_deadline == item.submission_deadline,
                    )
                )).scalar_one_or_none()
                if t:
                    t.file_id = fid
                    t.supporting_doc = fid
                    if fn:
                        t.file_name = fn
                    counts["tasks"] += 1

            for item in submissions:
                val = getattr(item, "file_id", None) or getattr(item, "submitted_file", None)
                if not val:
                    continue
                fid, fn = await _migrate_one(val, getattr(item, "file_name", None) or f"submission_{item.id}")
                if not fid:
                    continue
                mapped_tid = id_maps.get("task", {}).get(item.task_id)
                mapped_uid = id_maps.get("user", {}).get(item.user_id)
                if not mapped_tid or not mapped_uid:
                    continue
                s = (await session.execute(
                    select(TaskSubmission).where(
                        TaskSubmission.task_id == mapped_tid,
                        TaskSubmission.user_id == mapped_uid,
                    )
                )).scalar_one_or_none()
                if s:
                    s.file_id = fid
                    s.submitted_file = fid
                    if fn:
                        s.file_name = fn
                    counts["submissions"] += 1

            for item in infos:
                val = getattr(item, "file_id", None) or getattr(item, "file_url", None)
                if not val:
                    continue
                fid, fn = await _migrate_one(val, getattr(item, "file_name", None) or f"info_{item.id}")
                if not fid:
                    continue
                inf = (await session.execute(
                    select(Info).where(
                        Info.title == item.title,
                        Info.created_at == item.created_at,
                    )
                )).scalar_one_or_none()
                if inf:
                    inf.file_id = fid
                    inf.file_url = fid
                    if fn:
                        inf.file_name = fn
                    counts["infos"] += 1

            for item in notes:
                val = getattr(item, "file_id", None) or getattr(item, "file_url", None)
                if not val:
                    continue
                fid, fn = await _migrate_one(val, getattr(item, "file_name", None) or f"note_{item.id}")
                if not fid:
                    continue
                n = (await session.execute(
                    select(Note).where(
                        Note.title == item.title,
                        Note.department == item.department,
                        Note.created_at == item.created_at,
                    )
                )).scalar_one_or_none()
                if n:
                    n.file_id = fid
                    n.file_url = fid
                    if fn:
                        n.file_name = fn
                    counts["notes"] += 1

    return counts


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
                    existing.status = item.status
                else:
                    session.add(
                        InternAttendance(
                            attendance_id=mapped_attendance_id,
                            user_id=mapped_user_id,
                            enter_at=item.enter_at,
                            left_at=item.left_at,
                            status=item.status,
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


async def _sync_user_complains(sessionmaker, items):
    async with sessionmaker() as session:
        async with session.begin():
            for item in items:
                existing = (
                    await session.execute(
                        select(UserComplain).where(
                            UserComplain.content == item.content,
                            UserComplain.created_at == item.created_at,
                        )
                    )
                ).scalar_one_or_none()
                if existing:
                    _copy_fields(existing, item, UserComplain.__table__, ("id", "created_at"))
                else:
                    session.add(UserComplain(
                        content=item.content,
                        complain_type=item.complain_type,
                        department=item.department,
                        group=item.group,
                    ))


async def _sync_leave_requests(sessionmaker, items, id_maps):
    async with sessionmaker() as session:
        async with session.begin():
            for item in items:
                mapped_user_id = id_maps.get("user", {}).get(item.user_id)
                if not mapped_user_id:
                    logger.warning("Skipping leave %s: user %s not mapped", item.id, item.user_id)
                    continue

                mapped_reviewer = id_maps.get("user", {}).get(item.reviewed_by) if item.reviewed_by else None

                existing = (
                    await session.execute(
                        select(LeaveRequest).where(
                            LeaveRequest.user_id == mapped_user_id,
                            LeaveRequest.date == item.date,
                        )
                    )
                ).scalar_one_or_none()

                if existing:
                    _copy_fields(existing, item, LeaveRequest.__table__, ("id", "user_id", "created_at"))
                    existing.user_id = mapped_user_id
                    if mapped_reviewer:
                        existing.reviewed_by = mapped_reviewer
                else:
                    new = LeaveRequest(
                        user_id=mapped_user_id,
                        date=item.date,
                        reason=item.reason,
                        status=item.status,
                        reviewed_by=mapped_reviewer,
                    )
                    session.add(new)


async def _sync_cleaning_groups(sessionmaker, items):
    async with sessionmaker() as session:
        async with session.begin():
            for item in items:
                existing = (
                    await session.execute(
                        select(CleaningGroup).where(CleaningGroup.name == item.name)
                    )
                ).scalar_one_or_none()
                if existing:
                    _copy_fields(existing, item, CleaningGroup.__table__, ("id", "created_at"))
                else:
                    session.add(CleaningGroup(
                        name=item.name,
                        department=item.department,
                        turn_order=item.turn_order,
                    ))


async def _sync_cleaning_members(sessionmaker, items):
    async with sessionmaker() as session:
        async with session.begin():
            for item in items:
                existing = (
                    await session.execute(
                        select(CleaningGroupMember).where(
                            CleaningGroupMember.group_id == item.group_id,
                            CleaningGroupMember.user_id == item.user_id,
                        )
                    )
                ).scalar_one_or_none()
                if existing:
                    existing.cycle_cleaned = item.cycle_cleaned
                else:
                    session.add(CleaningGroupMember(
                        group_id=item.group_id,
                        user_id=item.user_id,
                        cycle_cleaned=item.cycle_cleaned,
                    ))


async def _sync_cleaning_duties(sessionmaker, items):
    async with sessionmaker() as session:
        async with session.begin():
            for item in items:
                existing = (
                    await session.execute(
                        select(CleaningDuty).where(CleaningDuty.date == item.date)
                    )
                ).scalar_one_or_none()
                if existing:
                    _copy_fields(existing, item, CleaningDuty.__table__, ("id", "created_at"))
                else:
                    session.add(CleaningDuty(
                        group_id=item.group_id,
                        date=item.date,
                        status=item.status,
                        completed_at=item.completed_at,
                    ))


async def _sync_cleaning_completions(sessionmaker, items):
    async with sessionmaker() as session:
        async with session.begin():
            for item in items:
                existing = (
                    await session.execute(
                        select(CleaningCompletion).where(
                            CleaningCompletion.duty_id == item.duty_id,
                            CleaningCompletion.user_id == item.user_id,
                        )
                    )
                ).scalar_one_or_none()
                if existing:
                    existing.completed_at = item.completed_at
                else:
                    session.add(CleaningCompletion(
                        duty_id=item.duty_id,
                        user_id=item.user_id,
                        completed_at=item.completed_at,
                    ))
