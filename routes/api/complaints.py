import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from controllers.complaintController import (
    delete_complaint,
    export_complaints_csv,
    get_complaint,
    get_complaints,
)
from db.database import get_db
from models.user import User

router = APIRouter(prefix="/api/admin")


@router.get("/complaints")
async def list_complaints(
    complain_type: str | None = Query(None),
    department: str | None = Query(None),
    group: str | None = Query(None),
    format: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()

    if format == "csv":
        csv_data = await loop.run_in_executor(None, export_complaints_csv, db)
        return PlainTextResponse(
            csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=complaints.csv"},
        )

    items = await loop.run_in_executor(
        None, get_complaints, db, complain_type, department, group
    )
    return {"ok": True, "complaints": items}


@router.get("/complaints/{complaint_id}")
async def complaint_detail(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()
    item = await loop.run_in_executor(None, get_complaint, db, complaint_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return {"ok": True, "complaint": item}


@router.delete("/complaints/{complaint_id}")
async def delete_complaint_endpoint(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()
    ok = await loop.run_in_executor(None, delete_complaint, db, complaint_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return {"ok": True}
