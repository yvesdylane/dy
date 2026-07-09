import asyncio
import logging
from datetime import date, datetime

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from config import settings
from controllers.attendanceController import (
    create_attendance,
    get_group_for_date,
)
from controllers.face import (
    cosine_similarity,
    detect_faces,
    extract_embedding,
)
from db.database import get_db
from models.attendance import Attendance, InternAttendance
from models.leave import LeaveRequest
from models.enums import LeaveStatus
from models.user import FaceEmbedding, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/face")


@router.post("/scan")
async def face_scan(
    file: UploadFile,
    mode: str = Query("entry"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_bytes = await file.read()
    loop = asyncio.get_running_loop()
    results = await loop.run_in_executor(None, _process_scan, db, file_bytes, mode)
    return {"ok": True, "detected": results}


def _process_scan(db: Session, file_bytes: bytes, mode: str) -> list[dict]:
    faces = detect_faces(file_bytes)
    if not faces:
        return []

    threshold = 1.0 - settings.recognition_threshold

    stored = db.query(FaceEmbedding).all()
    user_ids = [se.user_id for se in stored]
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    stored_list = [(se.user_id, np.frombuffer(se.embedding, dtype=np.float32)) for se in stored]

    today = date.today()
    group = get_group_for_date(today)
    att = db.execute(
        select(Attendance).where(Attendance.date == today)
    ).scalar_one_or_none() if group else None

    exempted_ids = set()

    results = []
    for face in faces:
        emb = face["embedding"]
        bbox = face["bbox"]

        best_uid = None
        best_sim = 0.0
        for uid, stored_emb in stored_list:
            sim = cosine_similarity(emb, stored_emb)
            if sim > best_sim:
                best_sim = sim
                best_uid = uid

        if best_uid is None or best_sim < threshold:
            results.append({
                "user_id": None,
                "name": None,
                "surname": None,
                "similarity": None,
                "status": "no_match",
                "bbox": bbox,
            })
            continue

        user = users.get(best_uid)
        if not user:
            results.append({
                "user_id": None,
                "name": None,
                "surname": None,
                "similarity": None,
                "status": "no_match",
                "bbox": bbox,
            })
            continue

        if not exempted_ids:
            exempted_ids = {
                l.user_id
                for l in db.execute(
                    select(LeaveRequest).where(
                        LeaveRequest.date == today,
                        LeaveRequest.status == LeaveStatus.approved,
                    )
                ).scalars().all()
            }

        if user.id in exempted_ids:
            results.append({
                "user_id": user.id,
                "name": user.name,
                "surname": user.surname,
                "similarity": round(best_sim, 4),
                "status": "exempted",
                "bbox": bbox,
            })
            continue

        if att is None and group is not None:
            try:
                att = create_attendance(db, today)
            except ValueError:
                pass
            if att:
                db.flush()

        if att is None:
            results.append({
                "user_id": user.id,
                "name": user.name,
                "surname": user.surname,
                "similarity": round(best_sim, 4),
                "status": "no_attendance",
                "bbox": bbox,
            })
            continue

        ia = db.execute(
            select(InternAttendance).where(
                InternAttendance.attendance_id == att.id,
                InternAttendance.user_id == user.id,
            )
        ).scalar_one_or_none()

        if not ia:
            ia = InternAttendance(attendance_id=att.id, user_id=user.id)
            db.add(ia)
            db.flush()

        now = datetime.now()
        if mode == "entry" and ia.enter_at is None:
            ia.enter_at = now
            status = "entry_marked"
        elif mode == "exit" and ia.left_at is None:
            ia.left_at = now
            status = "exit_marked"
        else:
            status = "already_marked"

        results.append({
            "user_id": user.id,
            "name": user.name,
            "surname": user.surname,
            "similarity": round(best_sim, 4),
            "status": status,
            "bbox": bbox,
        })

    if att is not None:
        db.commit()
    return results


@router.post("/enroll/{user_id}")
async def face_enroll(
    user_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()
    file_bytes = await file.read()

    embedding = await loop.run_in_executor(None, extract_embedding, file_bytes)
    if embedding is None:
        raise HTTPException(status_code=400, detail="No face detected in image")

    def _enroll(db: Session):
        db.query(FaceEmbedding).filter(FaceEmbedding.user_id == user_id).delete()
        db.add(FaceEmbedding(user_id=user_id, embedding=embedding.tobytes()))
        db.commit()

    await loop.run_in_executor(None, _enroll, db)
    return {"ok": True}
