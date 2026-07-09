import logging

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from db.database import get_db
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/face")


@router.post("/scan")
async def face_scan(
    file: UploadFile,
    mode: str = Query("entry"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"ok": False, "detected": [], "disabled": True, "detail": "Face recognition is disabled (512MB RAM limit)"}


@router.post("/enroll/{user_id}")
async def face_enroll(
    user_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"ok": False, "disabled": True, "detail": "Face recognition is disabled (512MB RAM limit)"}
