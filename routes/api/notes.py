import asyncio
import logging
from io import BytesIO

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session
from telegram import InputFile

from auth.dependencies import get_current_user
from config import settings
from controllers.notesController import (
    NoteCreate,
    NoteUpdate,
    create_note,
    delete_note,
    get_note,
    get_notes,
    update_note,
)
from db.database import get_db
from models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin")


@router.get("/notes")
async def list_notes(
    q: str | None = Query(None, alias="q"),
    department: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()
    notes = await loop.run_in_executor(None, get_notes, db, q, department)
    return {"ok": True, "notes": notes}


@router.get("/notes/{note_id}")
async def note_detail(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()
    note = await loop.run_in_executor(None, get_note, db, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"ok": True, "note": note}


@router.post("/notes")
async def create_note_endpoint(
    request: Request,
    title: str = Form(...),
    content: str | None = Form(None),
    department: str | None = Form(None),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()
    bot = request.app.state.bot

    file_id = None
    file_name = None
    if file and file.filename:
        file_bytes = await file.read()
        try:
            msg = await bot.send_document(
                chat_id=settings.telegram_group_id,
                document=InputFile(BytesIO(file_bytes), filename=file.filename),
            )
            file_id = msg.document.file_id
            file_name = file.filename
        except Exception as e:
            logger.error("Failed to upload note file to Telegram: %s", e)

    data = NoteCreate(
        title=title,
        content=content,
        department=department,
        file_id=file_id,
        file_name=file_name,
    )
    note = await loop.run_in_executor(None, create_note, db, current_user.id, data)
    return {"ok": True, "note": note}


@router.put("/notes/{note_id}")
async def update_note_endpoint(
    request: Request,
    note_id: int,
    title: str | None = Form(None),
    content: str | None = Form(None),
    department: str | None = Form(None),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()
    bot = request.app.state.bot

    file_id = None
    file_name = None
    if file and file.filename:
        file_bytes = await file.read()
        try:
            msg = await bot.send_document(
                chat_id=settings.telegram_group_id,
                document=InputFile(BytesIO(file_bytes), filename=file.filename),
            )
            file_id = msg.document.file_id
            file_name = file.filename
        except Exception as e:
            logger.error("Failed to upload note file to Telegram: %s", e)

    updates = {}
    if title is not None: updates["title"] = title
    if content is not None: updates["content"] = content
    if department is not None: updates["department"] = department
    if file_id: updates["file_id"] = file_id
    if file_name: updates["file_name"] = file_name

    data = NoteUpdate(**updates)
    note = await loop.run_in_executor(None, update_note, db, note_id, data)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"ok": True, "note": note}


@router.delete("/notes/{note_id}")
async def delete_note_endpoint(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()
    ok = await loop.run_in_executor(None, delete_note, db, note_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"ok": True}


@router.get("/notes/{note_id}/file")
async def download_note_file(
    note_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()
    note = await loop.run_in_executor(None, get_note, db, note_id)
    if note is None or not note.get("file_id"):
        raise HTTPException(status_code=404, detail="File not found")

    bot = request.app.state.bot
    tg_file = await bot.get_file(note["file_id"])
    file_bytes = bytes(await tg_file.download_as_bytearray())

    return Response(
        content=file_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{note["file_name"]}"'},
    )
