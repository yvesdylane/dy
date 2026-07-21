import logging
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.attendance import Attendance, InternAttendance
from models.enums import Department, Group, LeaveStatus
from models.leave import LeaveRequest
from models.user import User

logger = logging.getLogger(__name__)


def get_group_for_date(d: date) -> Group | None:
    wd = d.weekday()
    if wd == 6:
        return None  # Sunday
    return Group.A if wd in (0, 2, 4) else Group.B


def get_attendance(
    db: Session, d: date,
    departments: list[Department] | None = None,
    include_inactive: bool = False,
) -> dict:
    group = get_group_for_date(d)
    if group is None:
        return {"exists": False, "group": None, "students": [], "attendance_id": None}

    att = db.execute(
        select(Attendance).where(Attendance.date == d)
    ).scalar_one_or_none()

    conditions = [User.group.in_([group, Group.C]), User.role == "intern"]
    if departments:
        conditions.append(User.department.in_(departments))
    if not include_inactive:
        conditions.append(User.is_active == True)

    students = []
    interns = db.execute(
        select(User).where(*conditions)
    ).scalars().all()

    logger.info(
        "Attendance query | date=%s day_group=%s | found %d interns: %s",
        d, group.value if group else None, len(interns),
        [(u.id, u.name, u.surname, u.group.value if u.group else None) for u in interns],
    )

    # get approved leaves for this date
    exempted_user_ids = set()
    leaves = db.execute(
        select(LeaveRequest).where(
            LeaveRequest.date == d,
            LeaveRequest.status == LeaveStatus.approved,
        )
    ).scalars().all()
    exempted_user_ids = {l.user_id for l in leaves}

    if att:
        # map of existing entries
        entries = {
            ia.user_id: ia
            for ia in db.execute(
                select(InternAttendance).where(
                    InternAttendance.attendance_id == att.id
                )
            ).scalars().all()
        }
        for u in interns:
            entry = entries.get(u.id)
            is_exempted = u.id in exempted_user_ids
            students.append({
                "user_id": u.id,
                "name": u.name,
                "surname": u.surname,
                "enter_at": entry.enter_at.strftime("%H:%M") if entry and entry.enter_at and not isinstance(entry.enter_at, str) else None,
                "left_at": entry.left_at.strftime("%H:%M") if entry and entry.left_at and not isinstance(entry.left_at, str) else None,
                "status": "exempted" if is_exempted else (entry.status if entry else None),
            })
        return {
            "exists": True,
            "group": group.value,
            "students": students,
            "attendance_id": att.id,
        }
    else:
        for u in interns:
            is_exempted = u.id in exempted_user_ids
            students.append({
                "user_id": u.id,
                "name": u.name,
                "surname": u.surname,
                "enter_at": None,
                "left_at": None,
                "status": "exempted" if is_exempted else None,
            })
        return {
            "exists": False,
            "group": group.value,
            "students": students,
            "attendance_id": None,
        }


def create_attendance(
    db: Session, d: date,
    departments: list[Department] | None = None,
    include_inactive: bool = False,
) -> Attendance:
    group = get_group_for_date(d)
    if group is None:
        raise ValueError("Cannot create attendance for Sunday")
    existing = db.execute(
        select(Attendance).where(Attendance.date == d)
    ).scalar_one_or_none()
    if existing:
        raise ValueError("Attendance already exists for this date")

    att = Attendance(date=d, group=group)
    db.add(att)
    db.flush()
    db.refresh(att)

    # get exempted user ids
    exempted = set()
    leaves = db.execute(
        select(LeaveRequest).where(
            LeaveRequest.date == d,
            LeaveRequest.status == LeaveStatus.approved,
        )
    ).scalars().all()
    exempted = {l.user_id for l in leaves}

    conditions = [User.group.in_([group, Group.C]), User.role == "intern"]
    if departments:
        conditions.append(User.department.in_(departments))
    if not include_inactive:
        conditions.append(User.is_active == True)

    interns = db.execute(
        select(User).where(*conditions)
    ).scalars().all()

    for u in interns:
        is_exempted = u.id in exempted
        ia = InternAttendance(
            attendance_id=att.id,
            user_id=u.id,
            enter_at=datetime.combine(d, datetime.min.time()) if is_exempted else None,
            left_at=None,
            status="exempted" if is_exempted else None,
        )
        db.add(ia)
    db.flush()
    return att


def save_attendance(
    db: Session, attendance_id: int, entries: list[dict]
) -> None:
    att = db.get(Attendance, attendance_id)
    if not att:
        return
    att_date = att.date
    for entry in entries:
        uid = entry["user_id"]
        ia = db.execute(
            select(InternAttendance).where(
                InternAttendance.attendance_id == attendance_id,
                InternAttendance.user_id == uid,
            )
        ).scalar_one_or_none()
        if not ia:
            ia = InternAttendance(attendance_id=attendance_id, user_id=uid)
            db.add(ia)
            db.flush()
        enter_str = entry.get("enter_at")
        left_str = entry.get("left_at")

        if not enter_str and not left_str:
            db.delete(ia)
            continue

        if enter_str:
            ia.enter_at = datetime.combine(att_date, datetime.strptime(enter_str, "%H:%M").time())
        if left_str:
            ia.left_at = datetime.combine(att_date, datetime.strptime(left_str, "%H:%M").time())
    db.flush()


def delete_attendance(db: Session, d: date) -> bool:
    att = db.execute(
        select(Attendance).where(Attendance.date == d)
    ).scalar_one_or_none()
    if not att:
        return False
    db.query(InternAttendance).filter(
        InternAttendance.attendance_id == att.id
    ).delete()
    db.delete(att)
    db.flush()
    return True
