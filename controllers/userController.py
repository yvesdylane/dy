from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from models.enums import Department, Gender, Group, Role
from models.user import User


class UserCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    surname: str
    email: Optional[str] = None
    phone: str
    telegram_id: str
    gender: Gender
    role: Role
    department: Department
    group: Optional[Group] = None
    school: str
    dob: date
    image: Optional[str] = None
    quarter: Optional[int] = None
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
    quarter: Optional[int] = None
    fees_paid: Optional[float] = None
    total_fees: Optional[float] = None


def create_user(db: Session, data: UserCreate) -> User:
    user = User(**data.model_dump())
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


def search_users(
    db: Session,
    *,
    query: Optional[str] = None,
    role: Optional[Role] = None,
    department: Optional[Department] = None,
    group: Optional[Group] = None,
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
