import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from controllers.leaveController import list_leaves, review_leave
from db.database import get_db
from models.user import User

router = APIRouter(prefix="/api/admin")


@router.get("/leaves")
async def get_leaves(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()
    leaves = await loop.run_in_executor(None, list_leaves, db)
    return {"ok": True, "leaves": leaves}


@router.post("/leaves/{leave_id}/review")
async def review_leave_endpoint(
    leave_id: int,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    status = data.get("status")
    if status not in ("approved", "rejected"):
        raise HTTPException(400, "Invalid status")

    loop = asyncio.get_running_loop()
    lv = await loop.run_in_executor(
        None, review_leave, db, leave_id, status, current_user.id
    )
    if not lv:
        raise HTTPException(404, "Leave not found")
    return {"ok": True}
