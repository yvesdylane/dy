from fastapi import Request


def create_session(request: Request, user_id: int, telegram_id: str, role: str) -> None:
    request.session["user_id"] = user_id
    request.session["telegram_id"] = telegram_id
    request.session["role"] = role


def destroy_session(request: Request) -> None:
    request.session.clear()


def get_session_user_id(request: Request) -> int | None:
    return request.session.get("user_id")


def get_session_telegram_id(request: Request) -> str | None:
    return request.session.get("telegram_id")
