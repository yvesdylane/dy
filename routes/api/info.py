import asyncio
import logging
from io import BytesIO

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session
from telegram import InputFile

from auth.dependencies import get_current_user
from config import settings
from controllers.infoController import (
    InfoCreate,
    InfoUpdate,
    create_info,
    delete_info,
    get_info,
    get_infos,
    update_info,
)
from db.database import get_db
from models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin")


@router.get("/info")
async def list_info(
    q: str | None = Query(None, alias="q"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()
    items = await loop.run_in_executor(None, get_infos, db, q)
    return {"ok": True, "info": items}


@router.get("/info/{info_id}")
async def info_detail(
    info_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()
    item = await loop.run_in_executor(None, get_info, db, info_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Info not found")
    return {"ok": True, "info": item}


@router.post("/info")
async def create_info_endpoint(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
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
            logger.error("Failed to upload info file to Telegram: %s", e)

    data = InfoCreate(title=title, content=content, file_id=file_id, file_name=file_name)
    item = await loop.run_in_executor(None, create_info, db, current_user.id, data)
    return {"ok": True, "info": item}


@router.put("/info/{info_id}")
async def update_info_endpoint(
    request: Request,
    info_id: int,
    title: str | None = Form(None),
    content: str | None = Form(None),
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
            logger.error("Failed to upload info file to Telegram: %s", e)

    updates = {}
    if title is not None: updates["title"] = title
    if content is not None: updates["content"] = content
    if file_id: updates["file_id"] = file_id
    if file_name: updates["file_name"] = file_name

    data = InfoUpdate(**updates)
    item = await loop.run_in_executor(None, update_info, db, info_id, data)
    if item is None:
        raise HTTPException(status_code=404, detail="Info not found")
    return {"ok": True, "info": item}


@router.delete("/info/{info_id}")
async def delete_info_endpoint(
    info_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()
    ok = await loop.run_in_executor(None, delete_info, db, info_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Info not found")
    return {"ok": True}


@router.get("/info/{info_id}/file")
async def download_info_file(
    info_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()
    item = await loop.run_in_executor(None, get_info, db, info_id)
    if item is None or not item.get("file_id"):
        raise HTTPException(status_code=404, detail="File not found")

    bot = request.app.state.bot
    tg_file = await bot.get_file(item["file_id"])
    file_bytes = bytes(await tg_file.download_as_bytearray())

    return Response(
        content=file_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{item["file_name"]}"'},
    )
