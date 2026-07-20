import asyncio
import re
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from auth.session import create_session
from auth.telegram import verify_init_data
from controllers.auth import authenticate_telegram, register_new_user
from controllers.userController import get_user_by_phone, get_user_by_telegram_id, update_user, UserUpdate
from db.database import get_db
from helpers.phone import normalize_phone
from middleware.rate_limit import limiter

router = APIRouter()


@router.post("/auth/telegram")
@limiter.limit("10/minute")
async def telegram_auth(
    request: Request,
    initData: str = Form(...),
    db: Session = Depends(get_db),
):
    loop = asyncio.get_running_loop()
    try:
        user, tg_user = await loop.run_in_executor(
            None, authenticate_telegram, db, initData
        )
    except ValueError as e:
        return RedirectResponse(
            url=f"/?error={quote(str(e))}",
            status_code=302,
        )

    if user is None:
        return RedirectResponse(
            url=f"/register?telegram_id={tg_user.id}&first_name={quote(tg_user.first_name)}",
            status_code=302,
        )

    role = user.role.value
    create_session(request, user.id, str(tg_user.id), role)

    role_path = {
        "admin": "/admin",
        "super_admin": "/admin",
        "instructor": "/instructor",
        "intern": "/",
    }.get(role, "/")

    return RedirectResponse(url=role_path, status_code=302)


@router.post("/api/register")
@limiter.limit("5/minute")
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
@limiter.limit("5/minute")
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
    phone = normalize_phone(phone)

    def _link():
        existing = get_user_by_telegram_id(db, str(tg_user.id))
        if existing:
            raise ValueError("Telegram account already linked to another user")

        user = get_user_by_phone(db, phone)
        if user is None:
            raise ValueError("No user found with this phone number")

        if user.telegram_id and not re.search(r"[a-zA-Z]", user.telegram_id) and user.telegram_id != str(tg_user.id):
            raise ValueError("This account is already linked to a Telegram account")

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
