import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Form, UploadFile

from previouse.web.security import require_staff

logger = logging.getLogger(__name__)
router = APIRouter()


async def notify_interns(department, name, description, deadline):
    from sqlalchemy import select

    from previouse.bot.router import application as tg_app
    from previouse.db.database import async_session
    from previouse.models.models import Role, User

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
async def admin_list_tasks(user=Depends(require_staff)):
    from sqlalchemy import select

    from previouse.db.database import async_session
    from previouse.models.models import Task

    async with async_session() as session:
        tasks = (await session.execute(select(Task).order_by(Task.created_at.desc()))).scalars().all()

    return {"ok": True, "tasks": [{
        "id": t.id, "name": t.name, "description": t.description,
        "department": t.department.value,
        "supporting_doc": t.file_id or t.supporting_doc,
        "file_id": t.file_id,
        "file_name": t.file_name,
        "submission_deadline": t.submission_deadline.isoformat() if t.submission_deadline else None,
        "total_mark_on": t.total_mark_on,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    } for t in tasks]}


@router.post("/api/admin/tasks")
async def admin_create_task(
    staff_user=Depends(require_staff),
    name: str = Form(...), description: str = Form(...),
    department: str = Form(...), submission_deadline: str = Form(...),
    total_mark_on: int = Form(...), file: UploadFile = None,
):
    from previouse.db.database import async_session
    from previouse.models.models import Department, Task

    async with async_session() as session:
        async with session.begin():
            file_id = None
            file_name = None
            supporting_doc_legacy = None
            if file and file.filename:
                from previouse.bot.files import upload_file_to_group
                file_bytes = await file.read()
                try:
                    file_id, file_name = await upload_file_to_group(file_bytes, file.filename)
                except ValueError as e:
                    return {"ok": False, "detail": str(e)}
                supporting_doc_legacy = file_id

            task = Task(
                name=name, description=description,
                supporting_doc=supporting_doc_legacy,
                file_id=file_id, file_name=file_name,
                department=Department(department),
                submission_deadline=datetime.fromisoformat(submission_deadline),
                total_mark_on=total_mark_on, created_by=staff_user.id,
            )
            session.add(task)

    await notify_interns(task.department, task.name, task.description, str(task.submission_deadline))

    return {"ok": True, "task": {"id": task.id, "name": task.name, "department": task.department.value}}


@router.put("/api/admin/tasks/{task_id}")
async def admin_update_task(
    task_id: int, user=Depends(require_staff),
    name: str = Form(None), description: str = Form(None),
    department: str = Form(None), submission_deadline: str = Form(None),
    total_mark_on: int = Form(None), file: UploadFile = None,
):
    from previouse.db.database import async_session
    from previouse.models.models import Department, Task

    async with async_session() as session:
        async with session.begin():
            task = await session.get(Task, task_id)
            if not task:
                return {"ok": False, "detail": "Task not found"}

            if name is not None: task.name = name
            if description is not None: task.description = description
            if department is not None: task.department = Department(department)
            if submission_deadline is not None: task.submission_deadline = datetime.fromisoformat(submission_deadline)
            if total_mark_on is not None: task.total_mark_on = total_mark_on
            if file and file.filename:
                from previouse.bot.files import upload_file_to_group
                try:
                    file_id, file_name = await upload_file_to_group(await file.read(), file.filename)
                except ValueError as e:
                    return {"ok": False, "detail": str(e)}
                task.supporting_doc = file_id
                task.file_id = file_id
                task.file_name = file_name

    return {"ok": True}


@router.delete("/api/admin/tasks/{task_id}")
async def admin_delete_task(task_id: int, user=Depends(require_staff)):
    from previouse.db.database import async_session
    from previouse.models.models import Task

    async with async_session() as session:
        async with session.begin():
            task = await session.get(Task, task_id)
            if not task:
                return {"ok": False, "detail": "Task not found"}

            await session.delete(task)

    return {"ok": True}


@router.get("/api/admin/tasks/{task_id}/submissions")
async def admin_list_submissions(task_id: int, user=Depends(require_staff)):
    from sqlalchemy import select

    from previouse.db.database import async_session
    from previouse.models.models import Task, TaskSubmission, User

    async with async_session() as session:
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
        "submitted_file": ts.TaskSubmission.file_id or ts.TaskSubmission.submitted_file,
        "file_id": ts.TaskSubmission.file_id,
        "file_name": ts.TaskSubmission.file_name,
        "submitted_url": ts.TaskSubmission.submitted_url,
        "submitted_at": ts.TaskSubmission.submitted_at.isoformat() if ts.TaskSubmission.submitted_at else None,
        "mark_obtained": float(ts.TaskSubmission.mark_obtained) if ts.TaskSubmission.mark_obtained is not None else None,
        "feedback": ts.TaskSubmission.feedback,
    } for ts in rows]}


@router.put("/api/admin/submissions/{submission_id}")
async def admin_grade_submission(
    submission_id: int, user=Depends(require_staff),
    mark_obtained: float = Form(None), feedback: str = Form(None),
):
    from previouse.db.database import async_session
    from previouse.models.models import TaskSubmission

    async with async_session() as session:
        async with session.begin():
            sub = await session.get(TaskSubmission, submission_id)
            if not sub:
                return {"ok": False, "detail": "Submission not found"}

            if mark_obtained is not None:
                sub.mark_obtained = mark_obtained
            if feedback is not None:
                sub.feedback = feedback

    return {"ok": True, "submission": {"id": sub.id, "mark_obtained": float(sub.mark_obtained) if sub.mark_obtained is not None else None, "feedback": sub.feedback}}
