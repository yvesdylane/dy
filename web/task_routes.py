import logging
from datetime import datetime

from fastapi import APIRouter, Form, Query, UploadFile

from web.cloudinary import upload_to_cloudinary

logger = logging.getLogger(__name__)
router = APIRouter()


async def notify_interns(department, name, description, deadline):
    from sqlalchemy import select

    from bot.router import application as tg_app
    from db.database import async_session
    from models.models import Role, User

    if not tg_app:
        return

    async with async_session() as session:
        interns = (await session.execute(
            select(User).where(User.role == Role.intern, User.department == department)
        )).scalars().all()

    msg = f"📋 New Task: {name}\n\n{description[:200]}\n\nDepartment: {department.value}\nDeadline: {deadline}"
    for u in interns:
        if u.telegram_id and not u.telegram_id.startswith("pending_"):
            try:
                await tg_app.bot.send_message(chat_id=u.telegram_id, text=msg)
            except Exception:
                pass


@router.get("/api/admin/tasks")
async def admin_list_tasks(telegram_id: str = Query(...)):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import Role, Task, User

    async with async_session() as session:
        user = await session.execute(
            select(User).where(User.telegram_id == telegram_id, User.role.in_([Role.admin, Role.instructor]))
        )
        if not user.scalar_one_or_none():
            return {"ok": False, "detail": "Unauthorized"}

        tasks = (await session.execute(select(Task).order_by(Task.created_at.desc()))).scalars().all()

    return {"ok": True, "tasks": [{
        "id": t.id, "name": t.name, "description": t.description,
        "department": t.department.value, "supporting_doc": t.supporting_doc,
        "submission_deadline": t.submission_deadline.isoformat() if t.submission_deadline else None,
        "total_mark_on": t.total_mark_on,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    } for t in tasks]}


@router.post("/api/admin/tasks")
async def admin_create_task(
    telegram_id: str = Query(...),
    name: str = Form(...), description: str = Form(...),
    department: str = Form(...), submission_deadline: str = Form(...),
    total_mark_on: int = Form(...), file: UploadFile = None,
):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import Department, Role, Task, User

    async with async_session() as session:
        async with session.begin():
            user = await session.execute(
                select(User).where(User.telegram_id == telegram_id, User.role.in_([Role.admin, Role.instructor]))
            )
            user = user.scalar_one_or_none()
            if not user:
                return {"ok": False, "detail": "Unauthorized"}

            supporting_doc = None
            if file and file.filename:
                file_bytes = await file.read()
                supporting_doc = upload_to_cloudinary(file_bytes, folder="dy")

            task = Task(
                name=name, description=description, supporting_doc=supporting_doc,
                department=Department(department),
                submission_deadline=datetime.fromisoformat(submission_deadline),
                total_mark_on=total_mark_on, created_by=user.id,
            )
            session.add(task)

    await notify_interns(task.department, task.name, task.description, str(task.submission_deadline))

    return {"ok": True, "task": {"id": task.id, "name": task.name, "department": task.department.value}}


@router.put("/api/admin/tasks/{task_id}")
async def admin_update_task(
    task_id: int, telegram_id: str = Query(...),
    name: str = Form(None), description: str = Form(None),
    department: str = Form(None), submission_deadline: str = Form(None),
    total_mark_on: int = Form(None), file: UploadFile = None,
):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import Department, Role, Task, User

    async with async_session() as session:
        async with session.begin():
            user = await session.execute(
                select(User).where(User.telegram_id == telegram_id, User.role.in_([Role.admin, Role.instructor]))
            )
            if not user.scalar_one_or_none():
                return {"ok": False, "detail": "Unauthorized"}

            task = await session.get(Task, task_id)
            if not task:
                return {"ok": False, "detail": "Task not found"}

            if name is not None: task.name = name
            if description is not None: task.description = description
            if department is not None: task.department = Department(department)
            if submission_deadline is not None: task.submission_deadline = datetime.fromisoformat(submission_deadline)
            if total_mark_on is not None: task.total_mark_on = total_mark_on
            if file and file.filename:
                task.supporting_doc = upload_to_cloudinary(await file.read(), folder="dy")

    return {"ok": True}


@router.delete("/api/admin/tasks/{task_id}")
async def admin_delete_task(task_id: int, telegram_id: str = Query(...)):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import Role, Task, User

    async with async_session() as session:
        async with session.begin():
            user = await session.execute(
                select(User).where(User.telegram_id == telegram_id, User.role.in_([Role.admin, Role.instructor]))
            )
            if not user.scalar_one_or_none():
                return {"ok": False, "detail": "Unauthorized"}

            task = await session.get(Task, task_id)
            if not task:
                return {"ok": False, "detail": "Task not found"}

            await session.delete(task)

    return {"ok": True}


@router.get("/api/admin/tasks/{task_id}/submissions")
async def admin_list_submissions(task_id: int, telegram_id: str = Query(...)):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import Role, Task, TaskSubmission, User

    async with async_session() as session:
        user = await session.execute(
            select(User).where(User.telegram_id == telegram_id, User.role.in_([Role.admin, Role.instructor]))
        )
        if not user.scalar_one_or_none():
            return {"ok": False, "detail": "Unauthorized"}

        task = await session.get(Task, task_id)
        if not task:
            return {"ok": False, "detail": "Task not found"}

        result = await session.execute(
            select(TaskSubmission, User).join(User, TaskSubmission.user_id == User.id)
            .where(TaskSubmission.task_id == task_id).order_by(TaskSubmission.submitted_at.desc())
        )
        rows = result.all()

    return {"ok": True, "submissions": [{
        "id": ts.TaskSubmission.id,
        "user_name": ts.User.name,
        "user_surname": ts.User.surname,
        "submitted_file": ts.TaskSubmission.submitted_file,
        "submitted_at": ts.TaskSubmission.submitted_at.isoformat() if ts.TaskSubmission.submitted_at else None,
        "mark_obtained": float(ts.TaskSubmission.mark_obtained) if ts.TaskSubmission.mark_obtained is not None else None,
        "feedback": ts.TaskSubmission.feedback,
    } for ts in rows]}


@router.put("/api/admin/submissions/{submission_id}")
async def admin_grade_submission(
    submission_id: int, telegram_id: str = Query(...),
    mark_obtained: float = Form(None), feedback: str = Form(None),
):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import Role, TaskSubmission, User

    async with async_session() as session:
        async with session.begin():
            user = await session.execute(
                select(User).where(User.telegram_id == telegram_id, User.role.in_([Role.admin, Role.instructor]))
            )
            if not user.scalar_one_or_none():
                return {"ok": False, "detail": "Unauthorized"}

            sub = await session.get(TaskSubmission, submission_id)
            if not sub:
                return {"ok": False, "detail": "Submission not found"}

            if mark_obtained is not None:
                sub.mark_obtained = mark_obtained
            if feedback is not None:
                sub.feedback = feedback

    return {"ok": True, "submission": {"id": sub.id, "mark_obtained": float(sub.mark_obtained) if sub.mark_obtained is not None else None, "feedback": sub.feedback}}
