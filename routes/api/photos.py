import asyncio
import logging
import os
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from telegram import InputFile

from auth.dependencies import get_current_user
from config import settings
from controllers.face import extract_embedding, resize_for_cache
from db.database import get_db
from models.user import FaceEmbedding, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin")
CACHE_DIR = "uploads/cache/users"


def _get_user(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def _delete_embeddings(db: Session, user_id: int):
    db.query(FaceEmbedding).filter(FaceEmbedding.user_id == user_id).delete()


def _save_embedding(db: Session, user_id: int, embedding_bytes: bytes):
    emb = FaceEmbedding(user_id=user_id, embedding=embedding_bytes)
    db.add(emb)


@router.post("/users/{user_id}/photo")
async def upload_user_photo(
    user_id: int,
    request: Request,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bot = request.app.state.bot
    loop = asyncio.get_running_loop()

    file_bytes = await file.read()
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files allowed")

    # send to Telegram group
    try:
        msg = await bot.send_photo(
            chat_id=settings.telegram_group_id,
            photo=InputFile(BytesIO(file_bytes), filename=file.filename or "photo.jpg"),
        )
        file_id = msg.photo[-1].file_id
    except Exception as e:
        logger.error("Failed to upload photo to Telegram: %s", e)
        raise HTTPException(status_code=502, detail="Failed to upload photo to Telegram")

    # download full quality from Telegram
    try:
        tg_file = await bot.get_file(file_id)
        full_bytes = bytes(await tg_file.download_as_bytearray())
    except Exception as e:
        logger.error("Failed to download file from Telegram: %s", e)
        raise HTTPException(status_code=502, detail="Failed to download photo from Telegram")

    # cache thumbnail locally
    os.makedirs(CACHE_DIR, exist_ok=True)
    thumb = await loop.run_in_executor(None, resize_for_cache, full_bytes)
    cache_path = os.path.join(CACHE_DIR, f"{user_id}.jpg")
    await loop.run_in_executor(None, lambda: open(cache_path, "wb").write(thumb))

    # save file_id in user record
    user = await loop.run_in_executor(None, _get_user, db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.image = file_id
    db.commit()

    # extract face embedding
    embedding = await loop.run_in_executor(None, extract_embedding, full_bytes)
    if embedding is not None:
        await loop.run_in_executor(None, _delete_embeddings, db, user_id)
        emb_bytes = embedding.tobytes()
        await loop.run_in_executor(None, _save_embedding, db, user_id, emb_bytes)
        db.commit()
        logger.info("Face embedding stored for user %d", user_id)
    else:
        logger.warning("No face found in photo for user %d — embedding not stored", user_id)

    return {"ok": True, "photo_url": f"/api/admin/users/{user_id}/photo"}


@router.get("/users/{user_id}/photo")
async def serve_user_photo(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bot = request.app.state.bot
    loop = asyncio.get_running_loop()

    cache_path = os.path.join(CACHE_DIR, f"{user_id}.jpg")
    if os.path.exists(cache_path):
        return FileResponse(cache_path, media_type="image/jpeg")

    user = await loop.run_in_executor(None, _get_user, db, user_id)
    if not user or not user.image:
        raise HTTPException(status_code=404, detail="No photo available")

    try:
        tg_file = await bot.get_file(user.image)
        full_bytes = bytes(await tg_file.download_as_bytearray())
    except Exception as e:
        logger.error("Failed to download photo from Telegram: %s", e)
        raise HTTPException(status_code=502, detail="Failed to download photo")

    os.makedirs(CACHE_DIR, exist_ok=True)
    thumb = await loop.run_in_executor(None, resize_for_cache, full_bytes)
    await loop.run_in_executor(None, lambda: open(cache_path, "wb").write(thumb))

    return Response(content=thumb, media_type="image/jpeg")


@router.delete("/users/{user_id}/photo")
async def delete_user_photo(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()

    user = await loop.run_in_executor(None, _get_user, db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.image = None
    await loop.run_in_executor(None, _delete_embeddings, db, user_id)
    db.commit()

    cache_path = os.path.join(CACHE_DIR, f"{user_id}.jpg")
    if os.path.exists(cache_path):
        await loop.run_in_executor(None, os.remove, cache_path)
    return {"ok": True}
