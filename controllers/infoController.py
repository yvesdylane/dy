from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.infoNote import Info
from models.user import User


class InfoCreate(BaseModel):
    title: str
    content: str
    file_id: Optional[str] = None
    file_name: Optional[str] = None


class InfoUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    file_id: Optional[str] = None
    file_name: Optional[str] = None


def _to_dict(info: Info, creator_name: str | None = None, creator_surname: str | None = None) -> dict:
    return {
        "id": info.id,
        "title": info.title,
        "content": info.content,
        "file_id": info.file_id,
        "file_name": info.file_name,
        "created_by": info.created_by,
        "created_at": info.created_at.isoformat() if info.created_at else None,
        "updated_at": info.updated_at.isoformat() if info.updated_at else None,
        "creator_name": creator_name,
        "creator_surname": creator_surname,
    }


def get_infos(db: Session, query: str | None = None) -> list[dict]:
    stmt = (
        select(Info, User.name, User.surname)
        .join(User, Info.created_by == User.id)
    )
    if query:
        stmt = stmt.where(Info.title.ilike(f"%{query}%"))
    stmt = stmt.order_by(Info.created_at.desc())
    rows = db.execute(stmt).all()
    return [_to_dict(info, cn, cs) for info, cn, cs in rows]


def get_info(db: Session, info_id: int) -> dict | None:
    row = (
        db.execute(
            select(Info, User.name, User.surname)
            .join(User, Info.created_by == User.id)
            .where(Info.id == info_id)
        )
        .first()
    )
    if row is None:
        return None
    info, cn, cs = row
    return _to_dict(info, cn, cs)


def create_info(db: Session, user_id: int, data: InfoCreate) -> dict:
    info = Info(
        title=data.title,
        content=data.content,
        file_id=data.file_id,
        file_name=data.file_name,
        created_by=user_id,
    )
    db.add(info)
    db.flush()
    db.refresh(info)
    return _to_dict(info)


def update_info(db: Session, info_id: int, data: InfoUpdate) -> dict | None:
    info = db.get(Info, info_id)
    if info is None:
        return None
    updates = data.model_dump(exclude_unset=True)
    for key, val in updates.items():
        setattr(info, key, val)
    info.updated_at = datetime.utcnow()
    db.flush()
    db.refresh(info)
    user = db.get(User, info.created_by)
    return _to_dict(info, user.name if user else None, user.surname if user else None)


def delete_info(db: Session, info_id: int) -> bool:
    info = db.get(Info, info_id)
    if info is None:
        return False
    db.delete(info)
    db.flush()
    return True
