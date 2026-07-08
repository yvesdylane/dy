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
    file_id = None
    if bot is not None:
        try:
            msg = await bot.send_photo(
                chat_id=settings.telegram_group_id,
                photo=InputFile(BytesIO(file_bytes), filename=file.filename or "photo.jpg"),
            )
            file_id = msg.photo[-1].file_id
        except Exception as e:
            logger.warning("Current bot failed to upload photo: %s", e)
    if file_id is None and settings.old_bot_token:
        logger.info("Trying old_bot_token to upload photo")
        file_id = await loop.run_in_executor(
            None, _try_upload, settings.old_bot_token,
            settings.telegram_group_id, file_bytes, file.filename or "photo.jpg",
        )
    if file_id is None:
        raise HTTPException(status_code=502, detail="Failed to upload photo to Telegram")

    # download full quality from Telegram
    full_bytes = None
    if bot is not None:
        try:
            tg_file = await bot.get_file(file_id)
            full_bytes = bytes(await tg_file.download_as_bytearray())
        except Exception as e:
            logger.warning("Current bot failed to download after upload: %s", e)
    if full_bytes is None and settings.old_bot_token:
        logger.info("Trying old_bot_token to download after upload")
        full_bytes = await loop.run_in_executor(None, _try_download, settings.old_bot_token, file_id)
    if full_bytes is None:
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


def _count_embeddings(db: Session, user_id: int) -> int:
    return db.query(FaceEmbedding).filter(FaceEmbedding.user_id == user_id).count()


@router.post("/users/{user_id}/embeddings")
async def add_user_embedding(
    user_id: int,
    request: Request,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()

    file_bytes = await file.read()
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files allowed")

    user = await loop.run_in_executor(None, _get_user, db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    embedding = await loop.run_in_executor(None, extract_embedding, file_bytes)
    if embedding is None:
        raise HTTPException(status_code=400, detail="No face detected in image")

    emb_bytes = embedding.tobytes()
    await loop.run_in_executor(None, _save_embedding, db, user_id, emb_bytes)
    db.commit()

    count = await loop.run_in_executor(None, _count_embeddings, db, user_id)
    logger.info("Face embedding appended for user %d (total %d)", user_id, count)
    return {"ok": True, "embeddings_count": count}


TELEGRAM_FILE_API = "https://api.telegram.org/bot{token}/getFile?file_id={file_id}"
TELEGRAM_DL_API = "https://api.telegram.org/file/bot{token}/{file_path}"


def _try_download(token: str, file_id: str) -> bytes | None:
    import httpx
    try:
        info_resp = httpx.get(
            TELEGRAM_FILE_API.format(token=token, file_id=file_id),
            timeout=15,
        )
        info_resp.raise_for_status()
        file_path = info_resp.json()["result"]["file_path"]
        dl_resp = httpx.get(
            TELEGRAM_DL_API.format(token=token, file_path=file_path),
            timeout=30,
        )
        dl_resp.raise_for_status()
        return dl_resp.content
    except Exception:
        return None


TELEGRAM_SEND_PHOTO_API = "https://api.telegram.org/bot{token}/sendPhoto"


def _try_upload(token: str, chat_id: int, file_bytes: bytes, filename: str) -> str | None:
    import httpx
    try:
        resp = httpx.post(
            TELEGRAM_SEND_PHOTO_API.format(token=token),
            data={"chat_id": chat_id},
            files={"photo": (filename, file_bytes, "image/jpeg")},
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        if not result.get("ok"):
            return None
        photos = result["result"]["photo"]
        return photos[-1]["file_id"]
    except Exception:
        return None


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

    full_bytes = None
    if bot is not None:
        try:
            tg_file = await bot.get_file(user.image)
            full_bytes = bytes(await tg_file.download_as_bytearray())
        except Exception as e:
            logger.warning("Current bot failed to download photo for user %d: %s", user_id, e)

    if full_bytes is None and settings.old_bot_token:
        full_bytes = await loop.run_in_executor(None, _try_download, settings.old_bot_token, user.image)

    if full_bytes is None:
        raise HTTPException(status_code=404, detail="No photo available")

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
