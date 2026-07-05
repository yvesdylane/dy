import csv
import io
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.complaint import Complaint
from models.enums import ComplainType, Department, Group


class ComplaintOut(BaseModel):
    id: int
    content: str
    complain_type: str
    department: str
    group: Optional[str] = None
    created_at: str


def _to_dict(c: Complaint) -> dict:
    return {
        "id": c.id,
        "content": c.content,
        "complain_type": c.complain_type.value,
        "department": c.department.value,
        "group": c.group.value if c.group else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def get_complaints(
    db: Session,
    complain_type: str | None = None,
    department: str | None = None,
    group: str | None = None,
) -> list[dict]:
    stmt = select(Complaint)
    if complain_type:
        stmt = stmt.where(Complaint.complain_type == ComplainType(complain_type))
    if department:
        stmt = stmt.where(Complaint.department == Department(department))
    if group:
        stmt = stmt.where(Complaint.group == Group(group))
    stmt = stmt.order_by(Complaint.created_at.desc())
    rows = db.execute(stmt).all()
    return [_to_dict(row[0]) for row in rows]


def get_complaint(db: Session, complaint_id: int) -> dict | None:
    c = db.get(Complaint, complaint_id)
    if c is None:
        return None
    return _to_dict(c)


def delete_complaint(db: Session, complaint_id: int) -> bool:
    c = db.get(Complaint, complaint_id)
    if c is None:
        return False
    db.delete(c)
    db.flush()
    return True


def export_complaints_csv(db: Session) -> str:
    items = db.execute(select(Complaint).order_by(Complaint.created_at.desc())).scalars().all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Type", "Department", "Group", "Content", "Date"])
    for c in items:
        w.writerow([
            c.complain_type.value,
            c.department.value,
            c.group.value if c.group else "",
            c.content,
            c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else "",
        ])
    return buf.getvalue()
