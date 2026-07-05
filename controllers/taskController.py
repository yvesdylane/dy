import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.enums import Department
from models.task import Task
from models.user import User

TASK_UPLOAD_DIR = Path("uploads/tasks")


class TaskCreate(BaseModel):
    name: str
    description: str
    department: str
    submission_deadline: datetime
    total_mark_on: int
    supporting_doc: Optional[str] = None
    file_id: Optional[str] = None
    file_name: Optional[str] = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    supporting_doc: Optional[str] = None
    file_id: Optional[str] = None
    file_name: Optional[str] = None
    department: Optional[str] = None
    submission_deadline: datetime
    total_mark_on: int
    created_by: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    creator_name: Optional[str] = None
    creator_surname: Optional[str] = None


def _to_dict(task: Task, creator_name: str | None = None, creator_surname: str | None = None) -> dict:
    full = f"{creator_name} {creator_surname}" if creator_name else None
    return {
        "id": task.id,
        "name": task.name,
        "description": task.description,
        "supporting_doc": task.supporting_doc,
        "file_id": task.file_id,
        "file_name": task.file_name,
        "department": task.department.value if task.department else None,
        "submission_deadline": task.submission_deadline.isoformat(),
        "total_mark_on": task.total_mark_on,
        "created_by": task.created_by,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        "creator_name": creator_name,
        "creator_surname": creator_surname,
        "creator_full": full,
    }


def get_tasks(db: Session, query: str | None = None, department: str | None = None) -> list[dict]:
    stmt = (
        select(Task, User.name, User.surname)
        .join(User, Task.created_by == User.id)
    )
    if query:
        stmt = stmt.where(Task.name.ilike(f"%{query}%"))
    if department:
        stmt = stmt.where(Task.department == Department(department))
    stmt = stmt.order_by(Task.created_at.desc())
    rows = db.execute(stmt).all()
    return [_to_dict(task, cn, cs) for task, cn, cs in rows]


def get_task(db: Session, task_id: int) -> dict | None:
    row = (
        db.execute(
            select(Task, User.name, User.surname)
            .join(User, Task.created_by == User.id)
            .where(Task.id == task_id)
        )
        .first()
    )
    if row is None:
        return None
    task, creator_name, creator_surname = row
    return _to_dict(task, creator_name, creator_surname)


def create_task(db: Session, user_id: int, data: TaskCreate) -> dict:
    task = Task(
        name=data.name,
        description=data.description,
        department=Department(data.department),
        submission_deadline=data.submission_deadline,
        total_mark_on=data.total_mark_on,
        supporting_doc=data.supporting_doc,
        file_id=data.file_id,
        file_name=data.file_name,
        created_by=user_id,
    )
    db.add(task)
    db.flush()
    db.refresh(task)
    return _to_dict(task)


def save_task_file(file_bytes: bytes, original_filename: str) -> tuple[str, str]:
    TASK_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    unique = f"{uuid.uuid4().hex}_{original_filename}"
    path = TASK_UPLOAD_DIR / unique
    path.write_bytes(file_bytes)
    return unique, original_filename
