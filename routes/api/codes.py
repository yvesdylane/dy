import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from controllers.codesController import (
    create_codes,
    delete_code,
    delete_codes_batch,
    get_codes,
)
from db.database import get_db
from models.enums import Role
from models.user import User

router = APIRouter(prefix="/api/admin")


@router.get("/codes")
async def list_codes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()
    codes = await loop.run_in_executor(None, get_codes, db)
    return {
        "ok": True,
        "codes": [
            {
                "id": c.id,
                "code": c.code,
                "role": c.role.value,
                "is_used": c.is_used,
                "created_at": str(c.created_at),
                "expires_at": str(c.expires_at),
            }
            for c in codes
        ],
    }


@router.post("/codes")
async def generate_codes(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role_val = data.get("role", "intern")
    expiry_minutes = data.get("expiry_minutes", 60)
    count = min(data.get("count", 1), 100)

    loop = asyncio.get_running_loop()
    codes = await loop.run_in_executor(
        None,
        create_codes,
        db,
        Role(role_val),
        expiry_minutes,
        count,
        current_user.id,
    )
    return {
        "ok": True,
        "codes": [
            {"id": c.id, "code": c.code, "role": c.role.value} for c in codes
        ],
    }


@router.delete("/codes/{code_id}")
async def delete_code_endpoint(
    code_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()
    ok = await loop.run_in_executor(None, delete_code, db, code_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Code not found")
    return {"ok": True}


@router.post("/codes/delete-batch")
async def delete_codes_batch_endpoint(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()
    count = await loop.run_in_executor(
        None,
        delete_codes_batch,
        db,
        data.get("ids"),
        data.get("all", False),
    )
    return {"ok": True, "deleted": count}
