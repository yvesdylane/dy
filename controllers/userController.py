from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from models.enums import Department, Gender, Group, Role
from models.user import User


import secrets


class UserCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    surname: str
    email: Optional[str] = None
    phone: str
    telegram_id: Optional[str] = None
    gender: Gender
    role: Role
    department: Department
    group: Optional[Group] = None
    school: str
    dob: date
    image: Optional[str] = None
    quarter: Optional[str] = None
    fees_paid: Optional[float] = 0
    total_fees: Optional[float] = 40000


class UserUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = None
    surname: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    telegram_id: Optional[str] = None
    gender: Optional[Gender] = None
    role: Optional[Role] = None
    department: Optional[Department] = None
    group: Optional[Group] = None
    school: Optional[str] = None
    dob: Optional[date] = None
    image: Optional[str] = None
    quarter: Optional[str] = None
    is_active: Optional[bool] = None
    fees_paid: Optional[float] = None
    total_fees: Optional[float] = None


def _generate_fake_telegram_id(db: Session) -> str:
    for _ in range(100):
        suffix = secrets.token_hex(4)
        tid = f"dy_{suffix}"
        existing = db.execute(
            select(User).where(User.telegram_id == tid)
        ).scalar_one_or_none()
        if not existing:
            return tid
    raise ValueError("Could not generate unique telegram_id")


def create_user(db: Session, data: UserCreate) -> User:
    dump = data.model_dump()
    if dump.get("telegram_id") is None:
        dump["telegram_id"] = _generate_fake_telegram_id(db)
    user = User(**dump)
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_by_telegram_id(db: Session, telegram_id: str) -> User | None:
    return db.execute(
        select(User).where(User.telegram_id == telegram_id)
    ).scalar_one_or_none()


def get_user_by_phone(db: Session, phone: str) -> User | None:
    return db.execute(
        select(User).where(User.phone == phone)
    ).scalar_one_or_none()


def search_users(
    db: Session,
    *,
    query: Optional[str] = None,
    role: Optional[Role] = None,
    department: Optional[Department] = None,
    group: Optional[Group] = None,
    gender: Optional[Gender] = None,
    is_active: Optional[bool] = None,
    fees_paid_min: Optional[float] = None,
    fully_paid: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[User], int]:
    stmt = select(User)
    count_stmt = select(func.count(User.id))

    if query:
        pattern = f"%{query}%"
        clause = or_(
            User.name.ilike(pattern),
            User.surname.ilike(pattern),
            User.email.ilike(pattern),
        )
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)

    if role is not None:
        stmt = stmt.where(User.role == role)
        count_stmt = count_stmt.where(User.role == role)
    if department is not None:
        stmt = stmt.where(User.department == department)
        count_stmt = count_stmt.where(User.department == department)
    if group is not None:
        stmt = stmt.where(User.group == group)
        count_stmt = count_stmt.where(User.group == group)
    if gender is not None:
        stmt = stmt.where(User.gender == gender)
        count_stmt = count_stmt.where(User.gender == gender)

    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
        count_stmt = count_stmt.where(User.is_active == is_active)

    if fees_paid_min is not None:
        stmt = stmt.where(User.fees_paid >= fees_paid_min)
        count_stmt = count_stmt.where(User.fees_paid >= fees_paid_min)
    if fully_paid:
        stmt = stmt.where(User.fees_paid >= User.total_fees)
        count_stmt = count_stmt.where(User.fees_paid >= User.total_fees)

    total = db.scalar(count_stmt) or 0
    stmt = stmt.offset(skip).limit(limit).order_by(User.id.desc())
    users = list(db.execute(stmt).scalars().all())
    return users, total


def get_users(
    db: Session,
    *,
    role: Optional[Role] = None,
    department: Optional[Department] = None,
    group: Optional[Group] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[User]:
    stmt = select(User)
    if role is not None:
        stmt = stmt.where(User.role == role)
    if department is not None:
        stmt = stmt.where(User.department == department)
    if group is not None:
        stmt = stmt.where(User.group == group)
    stmt = stmt.offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def update_user(db: Session, user_id: int, data: UserUpdate) -> User | None:
    user = db.get(User, user_id)
    if user is None:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    user.updated_at = datetime.utcnow()
    db.flush()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> bool:
    user = db.get(User, user_id)
    if user is None:
        return False
    db.delete(user)
    db.flush()
    return True
