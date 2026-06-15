import logging
from datetime import date, datetime, time

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, select

from web.security import verified_tid

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_group(d: date):
    if d.weekday() == 6:
        return None
    from models.models import Group
    return Group.A if d.weekday() in (0, 2, 4) else Group.B


@router.get("/api/admin/attendance")
async def admin_get_attendance(telegram_id: str = Depends(verified_tid), date_str: str = Query(...)):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import Attendance, InternAttendance, Role, User

    async with async_session() as session:
        admin = await session.execute(
            select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
        )
        if not admin.scalar_one_or_none():
            return {"ok": False, "detail": "Unauthorized"}

        d = date.fromisoformat(date_str)
        grp = _get_group(d)

        att = await session.execute(
            select(Attendance).where(Attendance.date == d)
        )
        att = att.scalar_one_or_none()

        if att:
            students_raw = await session.execute(
                select(User).where(User.role == Role.intern, User.department == att.group)
            )
            students = students_raw.scalars().all()

            ia_rows = await session.execute(
                select(InternAttendance).where(InternAttendance.attendance_id == att.id)
            )
            ia_map = {ia.user_id: ia for ia in ia_rows.scalars().all()}

            student_list = []
            for s in students:
                ia = ia_map.get(s.id)
                student_list.append({
                    "user_id": s.id,
                    "name": s.name,
                    "surname": s.surname,
                    "enter_at": ia.enter_at.strftime("%H:%M") if ia and ia.enter_at else None,
                    "left_at": ia.left_at.strftime("%H:%M") if ia and ia.left_at else None,
                })

            return {
                "ok": True, "exists": True, "date": date_str,
                "group": att.group.value, "attendance_id": att.id,
                "students": student_list,
            }

    return {
        "ok": True, "exists": False, "date": date_str,
        "group": grp.value if grp else None, "students": [],
    }


@router.post("/api/admin/attendance/save")
async def admin_save_attendance(telegram_id: str = Depends(verified_tid), data: dict = None):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import Attendance, InternAttendance, Role, User

    async with async_session() as session:
        async with session.begin():
            admin = await session.execute(
                select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
            )
            if not admin.scalar_one_or_none():
                return {"ok": False, "detail": "Unauthorized"}

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
async def admin_create_attendance(telegram_id: str = Depends(verified_tid), data: dict = None):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import Attendance, Role, User

    async with async_session() as session:
        async with session.begin():
            admin = await session.execute(
                select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
            )
            if not admin.scalar_one_or_none():
                return {"ok": False, "detail": "Unauthorized"}

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
async def admin_delete_attendance(telegram_id: str = Depends(verified_tid), date_str: str = Query(...)):
    from sqlalchemy import delete, select

    from db.database import async_session
    from models.models import Attendance, InternAttendance, Role, User

    async with async_session() as session:
        async with session.begin():
            admin = await session.execute(
                select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
            )
            if not admin.scalar_one_or_none():
                return {"ok": False, "detail": "Unauthorized"}

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
