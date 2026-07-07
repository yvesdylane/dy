import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from db.database import get_db
from models.task import Task, TaskSubmission
from models.user import User

router = APIRouter()

PAGES = {
    "dashboard": "admin/sections/dashboard.html",
    "users": "admin/sections/users.html",
    "codes": "admin/sections/codes.html",
    "registers": "admin/sections/registers.html",
    "leaves": "admin/sections/leaves.html",
    "pass": "admin/sections/pass.html",
    "tasks": "admin/sections/tasks.html",
    "notes": "admin/sections/notes.html",
    "info": "admin/sections/info.html",
    "complaints": "admin/sections/complaints.html",
}


@router.get("/admin", response_class=HTMLResponse)
async def admin_shell(
    request: Request,
    user: User = Depends(get_current_user),
):
    templates = request.app.state.templates
    print(request.session)
    return templates.TemplateResponse(
        request=request, name="admin/index.html", context={"user": user}
    )


@router.get("/admin/page/{page_name}", response_class=HTMLResponse)
async def admin_page(
    request: Request,
    page_name: str,
    user: User = Depends(get_current_user),
):
    template = PAGES.get(page_name)
    if template is None:
        raise HTTPException(status_code=404)
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request, name=template, context={"user": user}
    )


@router.get("/admin/task/{task_id}", response_class=HTMLResponse)
async def task_detail_page(
    request: Request,
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    templates = request.app.state.templates
    loop = asyncio.get_running_loop()
    row = await loop.run_in_executor(
        None,
        lambda: db.execute(
            select(Task, User.name, User.surname)
            .join(User, Task.created_by == User.id)
            .where(Task.id == task_id)
        ).first(),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    task, creator_name, creator_surname = row

    submissions = await loop.run_in_executor(
        None,
        lambda: db.execute(
            select(TaskSubmission, User.name, User.surname)
            .join(User, TaskSubmission.user_id == User.id)
            .where(TaskSubmission.task_id == task_id)
            .order_by(TaskSubmission.submitted_at.desc())
        ).all(),
    )
    subs = [
        {
            "id": s.id,
            "user_id": s.user_id,
            "submitted_file": s.submitted_file,
            "file_id": s.file_id,
            "file_name": s.file_name,
            "submitted_url": s.submitted_url,
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
            "mark_obtained": float(s.mark_obtained) if s.mark_obtained else None,
            "feedback": s.feedback,
            "user_name": un,
            "user_surname": us,
        }
        for s, un, us in submissions
    ]

    return templates.TemplateResponse(
        request=request,
        name="admin/sections/task-detail.html",
        context={
            "user": user,
            "task": task,
            "creator_name": creator_name,
            "creator_surname": creator_surname,
            "submissions": subs,
        },
    )
