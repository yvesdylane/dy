import asyncio
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from controllers.attendanceController import (
    create_attendance,
    delete_attendance,
    get_attendance,
    save_attendance,
)
from db.database import get_db, run_in_session
from models.user import User

router = APIRouter(prefix="/api/admin")


@router.get("/attendance")
async def get_attendance_endpoint(
    date_str: str = Query(alias="date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(400, "Invalid date format")

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, get_attendance, db, d)
    return {"ok": True, **result}


@router.post("/attendance/create")
async def create_attendance_endpoint(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        d = date.fromisoformat(data["date"])
    except (ValueError, KeyError):
        raise HTTPException(400, "Invalid date")

    loop = asyncio.get_running_loop()
    try:
        att = await loop.run_in_executor(None, create_attendance, db, d)
        return {"ok": True, "attendance_id": att.id}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/attendance/save")
async def save_attendance_endpoint(
    data: dict,
    current_user: User = Depends(get_current_user),
):
    att_id = data.get("attendance_id")
    entries = data.get("entries", [])
    if not att_id:
        raise HTTPException(400, "attendance_id required")

    await run_in_session(save_attendance, att_id, entries)
    return {"ok": True}


@router.delete("/attendance")
async def delete_attendance_endpoint(
    date_str: str = Query(alias="date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(400, "Invalid date")

    loop = asyncio.get_running_loop()
    ok = await loop.run_in_executor(None, delete_attendance, db, d)
    if not ok:
        raise HTTPException(404, "No attendance found for this date")
    return {"ok": True}
