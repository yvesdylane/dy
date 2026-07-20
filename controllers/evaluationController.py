from datetime import date
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.orm import Session, joinedload

from models.enums import Department, Group, Role
from models.evaluation import DailyEvaluation
from models.user import User


CRITERIA = [
    "punctuality",
    "professionalism",
    "dressing",
    "conduct",
    "teamwork",
    "participation",
    "leadership",
    "presentation",
    "communication",
]


class EvaluationSave(BaseModel):
    user_id: int
    date: str
    punctuality: Optional[int] = None
    professionalism: Optional[int] = None
    dressing: Optional[int] = None
    conduct: Optional[int] = None
    teamwork: Optional[int] = None
    participation: Optional[int] = None
    leadership: Optional[int] = None
    presentation: Optional[int] = None
    communication: Optional[int] = None
    notes: Optional[str] = None


def _eval_to_dict(e: DailyEvaluation) -> dict:
    return {
        "id": e.id,
        "user_id": e.user_id,
        "date": e.date.isoformat() if e.date else None,
        "scorer_id": e.scorer_id,
        "punctuality": e.punctuality,
        "professionalism": e.professionalism,
        "dressing": e.dressing,
        "conduct": e.conduct,
        "teamwork": e.teamwork,
        "participation": e.participation,
        "leadership": e.leadership,
        "presentation": e.presentation,
        "communication": e.communication,
        "notes": e.notes,
        "total": sum(
            getattr(e, c) or 0 for c in CRITERIA
        ),
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "updated_at": e.updated_at.isoformat() if e.updated_at else None,
    }


def get_evaluations(
    db: Session,
    eval_date: date,
    departments: Optional[list[Department]] = None,
    include_inactive: bool = False,
) -> list[dict]:
    today_group = Group.A if eval_date.weekday() in (0, 2, 4) else Group.B
    stmt = (
        select(DailyEvaluation, User.name, User.surname, User.department, User.group, User.is_active)
        .join(User, DailyEvaluation.user_id == User.id)
        .where(DailyEvaluation.date == eval_date)
        .where(User.group.in_([today_group, Group.C]))
    )
    if not include_inactive:
        stmt = stmt.where(User.is_active == True)
    if departments:
        stmt = stmt.where(User.department.in_(departments))

    rows = db.execute(stmt.order_by(User.name)).all()
    result = []
    for ev, un, us, dept, grp, active in rows:
        d = _eval_to_dict(ev)
        d["user_name"] = un
        d["user_surname"] = us
        d["department"] = dept.value if dept else None
        d["group"] = grp.value if grp else None
        d["is_active"] = active
        result.append(d)
    return result


def get_missing_evaluations(
    db: Session,
    eval_date: date,
    departments: Optional[list[Department]] = None,
) -> list[dict]:
    from models.attendance import Attendance, InternAttendance

    today_group = Group.A if eval_date.weekday() in (0, 2, 4) else Group.B

    attended = (
        select(InternAttendance.user_id)
        .join(Attendance, InternAttendance.attendance_id == Attendance.id)
        .where(Attendance.date == eval_date)
    ).subquery()

    stmt = select(User.id, User.name, User.surname, User.department, User.group).where(
        User.role == Role.intern,
        User.is_active == True,
        User.group.in_([today_group, Group.C]),
        User.id.notin_(select(DailyEvaluation.user_id).where(DailyEvaluation.date == eval_date)),
        User.id.in_(attended),
    )
    if departments:
        stmt = stmt.where(User.department.in_(departments))

    rows = db.execute(stmt.order_by(User.name)).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "surname": r.surname,
            "department": r.department.value if r.department else None,
            "group": r.group.value if r.group else None,
        }
        for r in rows
    ]


def save_evaluation(db: Session, data: EvaluationSave, scorer_id: int) -> dict:
    eval_date = date.fromisoformat(data.date)
    existing = db.execute(
        select(DailyEvaluation).where(
            DailyEvaluation.user_id == data.user_id,
            DailyEvaluation.date == eval_date,
        )
    ).scalar_one_or_none()

    if existing:
        ev = existing
    else:
        ev = DailyEvaluation(
            user_id=data.user_id,
            date=eval_date,
        )
        db.add(ev)

    for field in CRITERIA:
        val = getattr(data, field, None)
        if val is not None:
            setattr(ev, field, val)
    if data.notes is not None:
        ev.notes = data.notes
    ev.scorer_id = scorer_id

    db.flush()
    db.refresh(ev)
    return _eval_to_dict(ev)


def create_evaluations(
    db: Session,
    eval_date: date,
    departments: Optional[list[Department]] = None,
) -> int:
    today_group = Group.A if eval_date.weekday() in (0, 2, 4) else Group.B

    conditions = [
        User.role == Role.intern,
        User.is_active == True,
        User.group.in_([today_group, Group.C]),
    ]
    if departments:
        conditions.append(User.department.in_(departments))

    interns = db.execute(
        select(User.id).where(*conditions)
    ).scalars().all()

    created = 0
    for uid in interns:
        existing = db.execute(
            select(DailyEvaluation).where(
                DailyEvaluation.user_id == uid,
                DailyEvaluation.date == eval_date,
            )
        ).scalar_one_or_none()
        if existing:
            continue
        db.add(DailyEvaluation(user_id=uid, date=eval_date))
        created += 1
    db.commit()
    return created


def get_user_evaluation(db: Session, user_id: int, eval_date: date) -> dict | None:
    ev = db.execute(
        select(DailyEvaluation).where(
            DailyEvaluation.user_id == user_id,
            DailyEvaluation.date == eval_date,
        )
    ).scalar_one_or_none()
    if ev is None:
        return None
    return _eval_to_dict(ev)
