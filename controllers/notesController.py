from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.enums import Department
from models.infoNote import Note
from models.user import User


class NoteCreate(BaseModel):
    title: str
    content: Optional[str] = None
    department: Optional[str] = None
    file_id: Optional[str] = None
    file_name: Optional[str] = None


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    department: Optional[str] = None
    file_id: Optional[str] = None
    file_name: Optional[str] = None


def _to_dict(note: Note, uploader_name: str | None = None, uploader_surname: str | None = None) -> dict:
    return {
        "id": note.id,
        "title": note.title,
        "content": note.content,
        "department": note.department.value if note.department else None,
        "file_id": note.file_id,
        "file_name": note.file_name,
        "uploaded_by": note.uploaded_by,
        "created_at": note.created_at.isoformat() if note.created_at else None,
        "updated_at": note.updated_at.isoformat() if note.updated_at else None,
        "uploader_name": uploader_name,
        "uploader_surname": uploader_surname,
    }


def get_notes(db: Session, query: str | None = None, department: str | None = None) -> list[dict]:
    stmt = (
        select(Note, User.name, User.surname)
        .join(User, Note.uploaded_by == User.id)
    )
    if query:
        stmt = stmt.where(Note.title.ilike(f"%{query}%"))
    if department:
        stmt = stmt.where(Note.department == Department(department))
    stmt = stmt.order_by(Note.created_at.desc())
    rows = db.execute(stmt).all()
    return [_to_dict(note, un, us) for note, un, us in rows]


def get_note(db: Session, note_id: int) -> dict | None:
    row = (
        db.execute(
            select(Note, User.name, User.surname)
            .join(User, Note.uploaded_by == User.id)
            .where(Note.id == note_id)
        )
        .first()
    )
    if row is None:
        return None
    note, un, us = row
    return _to_dict(note, un, us)


def create_note(db: Session, user_id: int, data: NoteCreate) -> dict:
    note = Note(
        title=data.title,
        content=data.content,
        department=Department(data.department) if data.department else None,
        file_id=data.file_id,
        file_name=data.file_name,
        uploaded_by=user_id,
    )
    db.add(note)
    db.flush()
    db.refresh(note)
    return _to_dict(note)


def update_note(db: Session, note_id: int, data: NoteUpdate) -> dict | None:
    note = db.get(Note, note_id)
    if note is None:
        return None
    updates = data.model_dump(exclude_unset=True)
    for key, val in updates.items():
        if key == "department":
            val = Department(val) if val else None
        setattr(note, key, val)
    note.updated_at = datetime.utcnow()
    db.flush()
    db.refresh(note)
    user = db.get(User, note.uploaded_by)
    return _to_dict(note, user.name if user else None, user.surname if user else None)


def delete_note(db: Session, note_id: int) -> bool:
    note = db.get(Note, note_id)
    if note is None:
        return False
    db.delete(note)
    db.flush()
    return True
