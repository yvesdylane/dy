import asyncio

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from auth.session import create_session
from auth.telegram import verify_init_data
from controllers.auth import authenticate_telegram, register_new_user
from controllers.userController import get_user_by_phone, get_user_by_telegram_id, update_user, UserUpdate
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

    role = user.role.value
    create_session(request, user.id, str(tg_user.id), role)

    role_path = {
        "admin": "/admin",
        "super_admin": "/admin",
        "instructor": "/instructor",
        "intern": "/",
    }.get(role, "/")

    return {"ok": True, "role": role, "redirect": role_path}


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

    role = user.role.value
    create_session(request, user.id, user.telegram_id, role)

    role_path = {
        "admin": "/admin",
        "super_admin": "/admin",
        "instructor": "/instructor",
        "intern": "/",
    }.get(role, "/")

    return {"ok": True, "role": role, "redirect": role_path}


@router.post("/auth/link")
async def link_account(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db),
):
    loop = asyncio.get_running_loop()

    try:
        tg_user = await loop.run_in_executor(None, verify_init_data, data["initData"])
    except ValueError as e:
        return {"ok": False, "detail": str(e)}

    phone = data.get("phone", "")
    if not phone:
        return {"ok": False, "detail": "Phone is required"}
    if not phone.startswith("+"):
        phone = "+237" + phone

    def _link():
        existing = get_user_by_telegram_id(db, str(tg_user.id))
        if existing:
            raise ValueError("Telegram account already linked to another user")

        user = get_user_by_phone(db, phone)
        if user is None:
            raise ValueError("No user found with this phone number")

        user.telegram_id = str(tg_user.id)
        db.flush()
        return user

    try:
        user = await loop.run_in_executor(None, _link)
    except ValueError as e:
        return {"ok": False, "detail": str(e)}

    create_session(request, user.id, str(tg_user.id), user.role.value)

    role_path = {
        "admin": "/admin",
        "super_admin": "/admin",
        "instructor": "/instructor",
        "intern": "/",
    }.get(user.role.value, "/")

    return {"ok": True, "role": user.role.value, "redirect": role_path}
