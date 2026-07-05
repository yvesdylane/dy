import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.orm import Session

from models.enums import Role
from models.user import CreationCode


def get_codes(db: Session) -> list[CreationCode]:
    return list(
        db.execute(
            select(CreationCode).order_by(CreationCode.created_at.desc())
        ).scalars().all()
    )


def create_codes(
    db: Session,
    role: Role,
    expiry_minutes: int = 60,
    count: int = 1,
    created_by: int = 0,
) -> list[CreationCode]:
    codes = []
    for _ in range(min(count, 100)):
        code = str(secrets.randbelow(900000) + 100000)
        while db.execute(
            select(CreationCode).where(CreationCode.code == code)
        ).scalar_one_or_none():
            code = str(secrets.randbelow(900000) + 100000)
        cc = CreationCode(
            code=code,
            role=role,
            expires_at=datetime.utcnow() + timedelta(minutes=expiry_minutes),
            created_by=created_by,
        )
        db.add(cc)
        codes.append(cc)
    db.flush()
    for c in codes:
        db.refresh(c)
    return codes


def delete_code(db: Session, code_id: int) -> bool:
    cc = db.get(CreationCode, code_id)
    if cc is None:
        return False
    db.delete(cc)
    db.flush()
    return True


def delete_codes_batch(
    db: Session, ids: Optional[list[int]] = None, all_: bool = False
) -> int:
    if all_:
        result = db.execute(sa_delete(CreationCode))
        db.flush()
        return result.rowcount
    if ids:
        result = db.execute(
            sa_delete(CreationCode).where(CreationCode.id.in_(ids))
        )
        db.flush()
        return result.rowcount
    return 0
