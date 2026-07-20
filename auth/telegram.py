import hashlib
import hmac
import json
import logging
import time
from urllib.parse import parse_qsl

from config import settings
from models.telegramUser import TelegramUser

logger = logging.getLogger(__name__)


def verify_init_data(init_data: str) -> TelegramUser:

    data = dict(parse_qsl(init_data))

    received_hash = data.pop("hash", None)

    if received_hash is None:
        logger.warning("Missing hash in init_data (keys: %s)", list(data.keys()))
        raise ValueError("Missing hash")

    tg_user_raw = data.get("user", "{}")
    try:
        tg_user_info = json.loads(tg_user_raw)
    except json.JSONDecodeError:
        tg_user_info = {}
    tg_id = tg_user_info.get("id", "?")
    tg_name = tg_user_info.get("first_name", "?")
    logger.info(
        "tg_user=%s (%s) | auth_date=%s | age=%.0fs | keys=%s",
        tg_id, tg_name,
        data.get("auth_date", "?"),
        time.time() - int(data.get("auth_date", 0)),
        [k for k in data.keys() if k != "user"],
    )

    data_check_string = "\n".join(
        f"{k}={v}"
        for k, v in sorted(data.items())
    )

    secret_key = hmac.new(
        b"WebAppData",
        settings.bot_token.encode(),
        hashlib.sha256,
    ).digest()

    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(
        calculated_hash,
        received_hash,
    ):
        logger.warning("Hash mismatch for tg_user %s (%s)", tg_id, tg_name)
        raise ValueError("Invalid Telegram signature")

    logger.info("Hash OK for tg_user %s (%s)", tg_id, tg_name)

    auth_date = int(data["auth_date"])

    if time.time() - auth_date > 3600:
        logger.warning("Auth expired for tg_user %s (age=%.0fs)", tg_id, time.time() - auth_date)
        raise ValueError("Telegram login expired")

    return TelegramUser.model_validate(tg_user_raw)