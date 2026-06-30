import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from config import settings
from models.telegramUser import TelegramUser


def verify_init_data(init_data: str) -> TelegramUser:

    data = dict(parse_qsl(init_data))

    received_hash = data.pop("hash", None)

    if received_hash is None:
        raise ValueError("Missing hash")

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
        raise ValueError("Invalid Telegram signature")

    auth_date = int(data["auth_date"])

    if time.time() - auth_date > 3600:
        raise ValueError("Telegram login expired")

    return TelegramUser.model_validate(
        json.loads(data["user"])
    )