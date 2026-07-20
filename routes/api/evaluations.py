import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from controllers.evaluationController import (
    CRITERIA,
    EvaluationSave,
    get_evaluations,
    get_missing_evaluations,
    save_evaluation,
)
from db.database import get_db
from models.enums import Department
from models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin")


@router.get("/evaluations")
async def list_evaluations(
    date: str = Query(...),
    departments: str | None = Query(None),
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import date as d_date

    try:
        eval_date = d_date.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    dept_list = None
    if departments:
        dept_list = [Department(d.strip()) for d in departments.split(",") if d.strip()]

    if include_inactive and current_user.role.value not in ("super_admin", "admin"):
        raise HTTPException(status_code=403, detail="Only admins can include inactive users")

    loop = asyncio.get_running_loop()
    evals = await loop.run_in_executor(
        None, get_evaluations, db, eval_date, dept_list, include_inactive
    )
    return {"ok": True, "evaluations": evals}


@router.get("/evaluations/missing")
async def missing_evaluations(
    date: str = Query(...),
    departments: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import date as d_date

    try:
        eval_date = d_date.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    dept_list = None
    if departments:
        dept_list = [Department(d.strip()) for d in departments.split(",") if d.strip()]

    loop = asyncio.get_running_loop()
    missing = await loop.run_in_executor(
        None, get_missing_evaluations, db, eval_date, dept_list
    )
    return {"ok": True, "missing": missing}


@router.post("/evaluations/save")
async def save_evaluation_endpoint(
    data: EvaluationSave,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    for field in CRITERIA:
        val = getattr(data, field, None)
        if val is not None and (val < 1 or val > 5):
            raise HTTPException(
                status_code=400,
                detail=f"{field} must be between 1 and 5",
            )

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None, save_evaluation, db, data, current_user.id
    )
    return {"ok": True, "evaluation": result}
