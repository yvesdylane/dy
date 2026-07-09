from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.telegram import verify_init_data
from controllers.userController import create_user, get_user_by_telegram_id, UserCreate
from helpers.phone import normalize_phone
from models.enums import Department, Gender, Group, Role
from models.user import CreationCode
from models.telegramUser import TelegramUser
from models.user import User


def authenticate_telegram(
    db: Session, init_data: str
) -> tuple[User | None, TelegramUser]:
    tg_user = verify_init_data(init_data)
    user = get_user_by_telegram_id(db, str(tg_user.id))
    return user, tg_user


def register_new_user(db: Session, data: dict) -> User:
    telegram_id = data.get("telegram_id", "")
    if not telegram_id or not isinstance(telegram_id, str):
        raise ValueError("telegram_id is required")

    phone = data.get("phone", "")
    if not phone:
        raise ValueError("Phone is required")
    phone = normalize_phone(phone)

    existing_tid = db.execute(
        select(User).where(User.telegram_id == telegram_id)
    ).scalar_one_or_none()
    if existing_tid:
        raise ValueError("User already registered")

    existing_phone = db.execute(
        select(User).where(User.phone == phone)
    ).scalar_one_or_none()
    if existing_phone:
        raise ValueError("A user with this phone number already exists. Link your existing account instead.")

    code_val = data.get("code", "")
    if not code_val:
        raise ValueError("Registration code is required")

    cc = db.execute(
        select(CreationCode).where(
            CreationCode.code == code_val,
            CreationCode.is_used == False,
            CreationCode.expires_at > datetime.utcnow(),
        )
    ).scalar_one_or_none()

    if not cc:
        raise ValueError("Invalid or expired registration code")

    role = cc.role
    cc.is_used = True

    user_data = UserCreate(
        name=data["name"],
        surname=data["surname"],
        phone=phone,
        telegram_id=telegram_id,
        gender=Gender(data["gender"]),
        role=role,
        department=Department(data["department"]),
        group=Group(data["group"]) if data.get("group") else None,
        school=data["school"],
        dob=datetime.strptime(data["dob"], "%Y-%m-%d").date(),
        email=data.get("email"),
        quarter=data.get("quarter"),
    )

    return create_user(db, user_data)
