import logging
from datetime import date, datetime, time

from fastapi import APIRouter, Depends, Query

from previouse.web.security import require_admin, require_staff

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_group(d: date):
    if d.weekday() == 6:
        return None
    from previouse.models.models import Group
    return Group.A if d.weekday() in (0, 2, 4) else Group.B


@router.get("/api/admin/attendance")
async def admin_get_attendance(user=Depends(require_staff), date_str: str = Query(...), department: str | None = Query(None)):
    from sqlalchemy import select

    from previouse.db.database import async_session
    from previouse.models.models import Attendance, Department, InternAttendance, LeaveRequest, LeaveStatus, Role, User

    async with async_session() as session:
        d = date.fromisoformat(date_str)
        grp = _get_group(d)

        att = await session.execute(
            select(Attendance).where(Attendance.date == d)
        )
        att = att.scalar_one_or_none()

        # Get approved leaves for this date
        exempted_user_ids = set()
        if att:
            leaves = (await session.execute(
                select(LeaveRequest).where(
                    LeaveRequest.date == d,
                    LeaveRequest.status == LeaveStatus.approved,
                )
            )).scalars().all()
            exempted_user_ids = {lr.user_id for lr in leaves}

        if att:
            stmt = select(User).where(User.role == Role.intern, User.group == att.group)
            # If instructor, auto-filter by their department unless overridden
            if user.role == Role.instructor:
                dept_filter = department or user.department.value
                stmt = stmt.where(User.department == Department(dept_filter))
            elif department:
                stmt = stmt.where(User.department == Department(department))

            students_raw = await session.execute(stmt)
            students = students_raw.scalars().all()

            ia_rows = await session.execute(
                select(InternAttendance).where(InternAttendance.attendance_id == att.id)
            )
            ia_map = {ia.user_id: ia for ia in ia_rows.scalars().all()}

            student_list = []
            for s in students:
                ia = ia_map.get(s.id)
                if ia and ia.status == "exempted":
                    student_list.append({
                        "user_id": s.id,
                        "name": s.name,
                        "surname": s.surname,
                        "status": "exempted",
                        "enter_at": None,
                        "left_at": None,
                    })
                elif s.id in exempted_user_ids:
                    student_list.append({
                        "user_id": s.id,
                        "name": s.name,
                        "surname": s.surname,
                        "status": "exempted",
                        "enter_at": None,
                        "left_at": None,
                    })
                else:
                    student_list.append({
                        "user_id": s.id,
                        "name": s.name,
                        "surname": s.surname,
                        "status": None,
                        "enter_at": ia.enter_at.strftime("%H:%M") if ia and ia.enter_at else None,
                        "left_at": ia.left_at.strftime("%H:%M") if ia and ia.left_at else None,
                    })

            return {
                "ok": True, "exists": True, "date": date_str,
                "group": att.group.value, "attendance_id": att.id,
                "students": student_list,
                "readonly": user.role == Role.instructor,
            }

    return {
        "ok": True, "exists": False, "date": date_str,
        "group": grp.value if grp else None, "students": [],
    }


@router.post("/api/admin/attendance/save")
async def admin_save_attendance(user=Depends(require_admin), data: dict = None):
    from sqlalchemy import select

    from previouse.db.database import async_session
    from previouse.models.models import Attendance, InternAttendance

    async with async_session() as session:
        async with session.begin():
            attendance_id = data["attendance_id"]
            att = await session.get(Attendance, attendance_id)
            if not att:
                return {"ok": False, "detail": "Attendance not found"}

            for entry in data.get("entries", []):
                user_id = entry["user_id"]
                enter_at = entry.get("enter_at")
                left_at = entry.get("left_at")
                existing = await session.execute(
                    select(InternAttendance).where(
                        InternAttendance.attendance_id == attendance_id,
                        InternAttendance.user_id == user_id,
                    )
                )
                ia = existing.scalar_one_or_none()

                # Skip exempted rows — they come from approved leaves
                if ia and ia.status == "exempted":
                    continue

                if enter_at or left_at:
                    if ia:
                        if enter_at:
                            ia.enter_at = datetime.combine(att.date, time.fromisoformat(enter_at))
                        if left_at:
                            ia.left_at = datetime.combine(att.date, time.fromisoformat(left_at))
                    else:
                        if not enter_at:
                            continue
                        ia = InternAttendance(
                            attendance_id=attendance_id, user_id=user_id,
                            enter_at=datetime.combine(att.date, time.fromisoformat(enter_at)),
                            left_at=datetime.combine(att.date, time.fromisoformat(left_at)) if left_at else None,
                        )
                        session.add(ia)
                else:
                    if ia:
                        await session.delete(ia)

    return {"ok": True}


@router.post("/api/admin/attendance/create")
async def admin_create_attendance(user=Depends(require_admin), data: dict = None):
    from sqlalchemy import select

    from previouse.db.database import async_session
    from previouse.models.models import Attendance

    async with async_session() as session:
        async with session.begin():
            d = date.fromisoformat(data["date"])
            grp = _get_group(d)
            if grp is None:
                return {"ok": False, "detail": "Cannot create attendance for Sunday"}

            exists = await session.execute(
                select(Attendance).where(Attendance.date == d)
            )
            if exists.scalar_one_or_none():
                return {"ok": False, "detail": "Attendance already exists for this date"}

            session.add(Attendance(date=d, group=grp))

    return {"ok": True}


@router.delete("/api/admin/attendance")
async def admin_delete_attendance(user=Depends(require_admin), date_str: str = Query(...)):
    from sqlalchemy import delete, select

    from previouse.db.database import async_session
    from previouse.models.models import Attendance, InternAttendance

    async with async_session() as session:
        async with session.begin():
            d = date.fromisoformat(date_str)
            att = await session.execute(
                select(Attendance).where(Attendance.date == d)
            )
            att = att.scalar_one_or_none()
            if not att:
                return {"ok": False, "detail": "Attendance not found"}

            await session.execute(
                delete(InternAttendance).where(InternAttendance.attendance_id == att.id)
            )
            await session.delete(att)

    return {"ok": True}
