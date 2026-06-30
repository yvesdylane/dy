import asyncio

from fastapi import APIRouter, Body, Depends, Request
from sqlalchemy.orm import Session

from auth.session import create_session
from controllers.auth import authenticate_telegram, register_new_user
from db.database import get_db

router = APIRouter()


@router.post("/auth/telegram")
async def telegram_auth(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db),
):
    loop = asyncio.get_running_loop()
    try:
        user, tg_user = await loop.run_in_executor(
            None, authenticate_telegram, db, data["initData"]
        )
    except ValueError as e:
        return {"ok": False, "detail": str(e)}

    if user is None:
        return {
            "needs_registration": True,
            "telegram_id": tg_user.id,
            "first_name": tg_user.first_name,
        }

    create_session(request, user.id, str(tg_user.id))

    role_path = {
        "admin": "/admin",
        "super_admin": "/admin",
        "instructor": "/instructor",
        "intern": "/",
    }.get(user.role.value, "/")

    return {"ok": True, "role": user.role.value, "redirect": role_path}


@router.post("/api/register")
async def register(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db),
):
    loop = asyncio.get_running_loop()
    try:
        user = await loop.run_in_executor(None, register_new_user, db, data)
    except ValueError as e:
        return {"ok": False, "detail": str(e)}

    create_session(request, user.id, user.telegram_id)

    role_path = {
        "admin": "/admin",
        "super_admin": "/admin",
        "instructor": "/instructor",
        "intern": "/",
    }.get(user.role.value, "/")

    return {"ok": True, "role": user.role.value, "redirect": role_path}
