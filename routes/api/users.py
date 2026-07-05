import asyncio
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, computed_field, field_serializer
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from controllers.userController import (
    UserCreate,
    UserUpdate,
    create_user,
    delete_user,
    get_user,
    search_users,
    update_user,
)
from db.database import get_db
from models.enums import Department, Group, Role
from models.user import User

router = APIRouter(prefix="/api/admin")


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    surname: str
    email: Optional[str] = None
    phone: str
    telegram_id: str
    gender: str
    role: str
    department: str
    group: Optional[str] = None
    school: str
    dob: date
    image: Optional[str] = None
    quarter: Optional[str] = None
    fees_paid: Optional[float] = None
    total_fees: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_serializer("dob")
    def serialize_dob(self, v: date) -> str:
        return v.isoformat()

    @computed_field
    @property
    def photo_url(self) -> Optional[str]:
        if self.image:
            return f"/api/admin/users/{self.id}/photo"
        return None

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, v: Optional[datetime]) -> Optional[str]:
        if v is None:
            return None
        return v.isoformat()


@router.get("/users")
async def list_users(
    q: Optional[str] = Query(None, alias="q"),
    role: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    group: Optional[str] = Query(None),
    gender: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role_enum = Role(role) if role else None
    dept_enum = Department(department) if department else None
    group_enum = Group(group) if group else None
    gender_enum = Gender(gender) if gender else None

    loop = asyncio.get_running_loop()
    users, total = await loop.run_in_executor(
        None,
        lambda: search_users(
            db,
            query=q,
            role=role_enum,
            department=dept_enum,
            group=group_enum,
            gender=gender_enum,
            skip=skip,
            limit=limit,
        ),
    )

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "users": [UserOut.model_validate(u).model_dump() for u in users],
    }


@router.post("/users")
async def create_user_by_id(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()
    user = await loop.run_in_executor(None, create_user, db, data)
    return UserOut.model_validate(user).model_dump()


@router.get("/users/{user_id}")
async def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()
    user = await loop.run_in_executor(None, get_user, db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut.model_validate(user).model_dump()


@router.put("/users/{user_id}")
async def update_user_by_id(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()
    user = await loop.run_in_executor(None, update_user, db, user_id, data)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut.model_validate(user).model_dump()


@router.delete("/users/{user_id}")
async def delete_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()
    ok = await loop.run_in_executor(None, delete_user, db, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True}
