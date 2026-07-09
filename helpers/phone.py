import re


def normalize_phone(phone: str) -> str:
    if phone.startswith("+"):
        return phone
    digits = re.sub(r"\D", "", phone)
    if not digits:
        return phone
    digits = digits.removeprefix("00")
    if digits.startswith("237"):
        return "+" + digits
    return "+237" + digits


def is_fake_telegram_id(tid: str | None) -> bool:
    if not tid:
        return True
    return bool(re.search(r"[a-zA-Z]", tid))
