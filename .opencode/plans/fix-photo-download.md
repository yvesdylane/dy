# Fix Photo Endpoint — Bot null check + old_bot_token fallback

## Changes to `routes/api/photos.py`

### 1. Add constants + helper (after CACHE_DIR, before first route)
```python
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
```

### 2. Rewrite `serve_user_photo` (lines 97-126)
```python
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
    # Try current bot first
    if bot is not None:
        try:
            tg_file = await bot.get_file(user.image)
            full_bytes = bytes(await tg_file.download_as_bytearray())
        except Exception as e:
            logger.warning("Current bot failed to download photo for user %d: %s", user_id, e)

    # Fallback to old_bot_token via direct HTTP API
    if full_bytes is None and settings.old_bot_token:
        full_bytes = await loop.run_in_executor(None, _try_download, settings.old_bot_token, user.image)

    if full_bytes is None:
        raise HTTPException(status_code=404, detail="No photo available")

    os.makedirs(CACHE_DIR, exist_ok=True)
    thumb = await loop.run_in_executor(None, resize_for_cache, full_bytes)
    await loop.run_in_executor(None, lambda: open(cache_path, "wb").write(thumb))

    return Response(content=thumb, media_type="image/jpeg")
```

This covers:
- ✅ Bot null check → 404 instead of crash
- ✅ `old_bot_token` fallback when current bot can't access file_id
- ✅ Cached files served directly (no bot needed)
- ✅ Embedding extraction in upload endpoint unchanged
