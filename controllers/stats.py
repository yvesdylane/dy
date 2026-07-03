from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.enums import Role
from models.leave import LeaveRequest
from models.infoNote import Note
from models.task import Task
from models.user import User


def get_stats(db: Session) -> dict:
    total_users = db.scalar(select(func.count(User.id)))
    interns = db.scalar(select(func.count(User.id)).where(User.role == Role.intern))
    instructors = db.scalar(
        select(func.count(User.id)).where(User.role == Role.instructor)
    )
    admins = db.scalar(
        select(func.count(User.id)).where(User.role == Role.admin)
    )
    super_admins = db.scalar(
        select(func.count(User.id)).where(User.role == Role.super_admin)
    )
    tasks = db.scalar(select(func.count(Task.id)))
    notes = db.scalar(select(func.count(Note.id)))
    leave_requests = db.scalar(select(func.count(LeaveRequest.id)))

    total_fees = db.scalar(
        select(func.coalesce(func.sum(User.total_fees), 0)).where(User.role == Role.intern)
    )
    paid_fees = db.scalar(
        select(func.coalesce(func.sum(User.fees_paid), 0)).where(User.role == Role.intern)
    )

    return {
        "total_users": total_users or 0,
        "interns": interns or 0,
        "instructors": instructors or 0,
        "admins": admins or 0,
        "super_admins": super_admins or 0,
        "tasks": tasks or 0,
        "notes": notes or 0,
        "leave_requests": leave_requests or 0,
        "total_fees": float(total_fees or 0),
        "paid_fees": float(paid_fees or 0),
    }
