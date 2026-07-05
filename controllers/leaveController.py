from sqlalchemy import select
from sqlalchemy.orm import Session

from models.attendance import InternAttendance
from models.enums import LeaveStatus
from models.leave import LeaveRequest
from models.user import User


def list_leaves(db: Session) -> list[dict]:
    leaves = db.execute(
        select(LeaveRequest).order_by(LeaveRequest.created_at.desc()).limit(200)
    ).scalars().all()

    result = []
    for lv in leaves:
        user = db.get(User, lv.user_id)
        reviewer = db.get(User, lv.reviewed_by) if lv.reviewed_by else None
        result.append({
            "id": lv.id,
            "user_id": lv.user_id,
            "user_name": f"{user.name} {user.surname}" if user else "Unknown",
            "department": user.department.value if user else "",
            "group": user.group.value if user and user.group else None,
            "date": lv.date.isoformat(),
            "reason": lv.reason,
            "status": lv.status.value,
            "reviewer_name": f"{reviewer.name} {reviewer.surname}" if reviewer else None,
            "created_at": lv.created_at.isoformat() if lv.created_at else None,
        })
    return result


def review_leave(db: Session, leave_id: int, status: str, reviewer_id: int) -> LeaveRequest | None:
    lv = db.get(LeaveRequest, leave_id)
    if not lv:
        return None
    lv.status = LeaveStatus(status)
    lv.reviewed_by = reviewer_id

    # if approved, auto-create exempted attendance entry
    if lv.status == LeaveStatus.approved:
        from controllers.attendanceController import get_group_for_date

        group = get_group_for_date(lv.date)
        if group:
            from models.attendance import Attendance

            att = db.execute(
                select(Attendance).where(Attendance.date == lv.date)
            ).scalar_one_or_none()
            if att:
                ia = db.execute(
                    select(InternAttendance).where(
                        InternAttendance.attendance_id == att.id,
                        InternAttendance.user_id == lv.user_id,
                    )
                ).scalar_one_or_none()
                if ia:
                    ia.status = "exempted"
                else:
                    ia = InternAttendance(
                        attendance_id=att.id,
                        user_id=lv.user_id,
                        enter_at=None,
                        left_at=None,
                        status="exempted",
                    )
                    db.add(ia)
    db.flush()
    db.refresh(lv)
    return lv
