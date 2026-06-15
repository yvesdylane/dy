import base64
import hashlib
import hmac
import json
import time

from fastapi import Header, HTTPException, Query, Request


def verify_init_data(init_data: str, bot_token: str) -> dict | None:
    try:
        parsed = {}
        for part in init_data.split("&"):
            k, _, v = part.partition("=")
            from urllib.parse import unquote
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


async def verified_tid(
    request: Request,
    tid_query: str = Query(None, alias="telegram_id"),
) -> str:
    from config import settings

    init_data = request.headers.get("X-Init-Data")
    if init_data:
        parsed = verify_init_data(init_data, settings.telegram_token)
        if parsed:
            return str(parsed["user"]["id"])
    if tid_query:
        return tid_query
    raise HTTPException(status_code=401, detail="Authentication required")
