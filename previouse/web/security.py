import base64
import hashlib
import hmac
import json
import logging
import time
from urllib.parse import unquote

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select

from previouse.config import settings

logger = logging.getLogger(__name__)


def verify_init_data(init_data: str, bot_token: str) -> dict | None:
    try:
        parsed = {}
        for part in init_data.split("&"):
            k, _, v = part.partition("=")
            parsed[k] = unquote(v)

        hash_val = parsed.pop("hash", None)
        if not hash_val:
            return None

        sorted_items = sorted(parsed.items(), key=lambda x: x[0])
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted_items)

        secret_key = hmac.new(
            b"WebAppData", bot_token.encode(), hashlib.sha256
        ).digest()
        calculated = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated, hash_val):
            return None

        if "user" in parsed:
            parsed["user"] = json.loads(parsed["user"])
        return parsed
    except Exception:
        return None


def create_qr_payload(telegram_id: str, bot_token: str) -> tuple[str, str]:
    from datetime import date

    payload = {
        "date": str(date.today()),
        "ts": int(time.time()),
        "tid": telegram_id,
    }
    payload_json = json.dumps(payload, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip("=")

    sig = hmac.new(
        bot_token.encode(), payload_b64.encode(), hashlib.sha256
    ).hexdigest()
    return payload_b64, sig


def verify_qr_payload(
    payload_b64: str, sig: str, bot_token: str, max_age: int = 3600
) -> dict | None:
    expected = hmac.new(
        bot_token.encode(), payload_b64.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None

    try:
        padded = payload_b64 + "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
    except Exception:
        return None

    if int(time.time()) - payload.get("ts", 0) > max_age:
        return None

    return payload


async def _resolve_telegram_id(request: Request) -> str:
    init_data = request.headers.get("X-Init-Data")
    if init_data:
        parsed = verify_init_data(init_data, settings.telegram_token)
        if parsed:
            return str(parsed["user"]["id"])

    if settings.allow_dev_telegram_id_auth:
        tid = request.query_params.get("telegram_id") or request.headers.get("X-Telegram-Id")
        if tid:
            logger.warning("DEV auth used for telegram_id=%s", tid)
            return tid

    raise HTTPException(status_code=401, detail="Authentication required")


async def verified_tid(request: Request) -> str:
    return await _resolve_telegram_id(request)


async def get_current_user(
    telegram_id: str = Depends(verified_tid),
):
    from previouse.db.database import async_session
    from previouse.models.models import User

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user


async def require_admin(user=Depends(get_current_user)):
    from previouse.models.models import Role
    if user.role not in (Role.admin, Role.super_admin):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def require_super_admin(user=Depends(get_current_user)):
    from previouse.models.models import Role
    if user.role != Role.super_admin:
        raise HTTPException(status_code=403, detail="Super admin access required")
    return user


async def require_staff(user=Depends(get_current_user)):
    from previouse.models.models import Role
    if user.role not in (Role.admin, Role.instructor, Role.super_admin):
        raise HTTPException(status_code=403, detail="Staff access required")
    return user
