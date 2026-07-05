import asyncio
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from controllers.taskController import (
    TaskCreate,
    create_task,
    get_task,
    get_tasks,
    save_task_file,
)
from db.database import get_db
from models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin")


@router.get("/tasks")
async def list_tasks(
    q: str | None = Query(None, alias="q"),
    department: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()
    tasks = await loop.run_in_executor(None, get_tasks, db, q, department)
    return {"ok": True, "tasks": tasks}


@router.get("/tasks/{task_id}")
async def task_detail(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()
    task = await loop.run_in_executor(None, get_task, db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"ok": True, "task": task}


@router.post("/tasks")
async def create_task_endpoint(
    name: str = Form(...),
    description: str = Form(...),
    department: str = Form(...),
    submission_deadline: str = Form(...),
    total_mark_on: int = Form(...),
    supporting_doc: str | None = Form(None),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()

    file_id = None
    file_name = None
    if file and file.filename:
        file_bytes = await file.read()
        file_id, file_name = await loop.run_in_executor(
            None, save_task_file, file_bytes, file.filename
        )

    data = TaskCreate(
        name=name,
        description=description,
        department=department,
        submission_deadline=submission_deadline,
        total_mark_on=total_mark_on,
        supporting_doc=supporting_doc,
        file_id=file_id,
        file_name=file_name,
    )
    task = await loop.run_in_executor(None, create_task, db, current_user.id, data)
    return {"ok": True, "task": task}
