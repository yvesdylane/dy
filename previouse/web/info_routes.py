import logging

from fastapi import APIRouter, Depends, Form, UploadFile

from previouse.web.security import require_staff

logger = logging.getLogger(__name__)
router = APIRouter()


async def notify_interns(title, content, file_id=None, file_name=None):
    from sqlalchemy import select

    from previouse.bot.router import application as tg_app
    from previouse.db.database import async_session
    from previouse.models.models import Role, User

    if not tg_app:
        return

    async with async_session() as session:
        users = (await session.execute(
            select(User).where(User.role.in_([Role.intern, Role.instructor, Role.admin]))
        )).scalars().all()

    msg = f"📢 Announcement: {title}\n\n{content}"
    for u in users:
        if u.telegram_id and not u.telegram_id.startswith("pending_"):
            try:
                if file_id:
                    await tg_app.bot.send_document(
                        chat_id=u.telegram_id, document=file_id,
                        filename=file_name, caption=msg,
                    )
                else:
                    await tg_app.bot.send_message(chat_id=u.telegram_id, text=msg)
            except Exception:
                pass


@router.get("/api/admin/info")
async def admin_list_info(user=Depends(require_staff)):
    from sqlalchemy import select

    from previouse.db.database import async_session
    from previouse.models.models import Info

    async with async_session() as session:
        info = (await session.execute(
            select(Info).order_by(Info.created_at.desc())
        )).scalars().all()

    return {"ok": True, "info": [{
        "id": item.id, "title": item.title, "content": item.content,
        "file_url": item.file_id or item.file_url,
        "file_id": item.file_id,
        "file_name": item.file_name,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    } for item in info]}


@router.post("/api/admin/info")
async def admin_create_info(
    staff_user=Depends(require_staff),
    title: str = Form(...), content: str = Form(...),
    file: UploadFile = None,
):
    from previouse.db.database import async_session
    from previouse.models.models import Info

    async with async_session() as session:
        async with session.begin():
            file_id = None
            file_name = None
            file_url_for_legacy = None
            if file and file.filename:
                from previouse.bot.files import upload_file_to_group
                try:
                    file_id, file_name = await upload_file_to_group(await file.read(), file.filename)
                except ValueError as e:
                    return {"ok": False, "detail": str(e)}
                file_url_for_legacy = file_id

            item = Info(
                title=title, content=content,
                file_url=file_url_for_legacy, file_id=file_id, file_name=file_name,
                created_by=staff_user.id,
            )
            session.add(item)

    await notify_interns(item.title, item.content, file_id, file_name)

    return {"ok": True, "info": {"id": item.id, "title": item.title}}


@router.put("/api/admin/info/{info_id}")
async def admin_update_info(
    info_id: int, user=Depends(require_staff),
    title: str = Form(None), content: str = Form(None),
    file: UploadFile = None,
):
    from previouse.db.database import async_session
    from previouse.models.models import Info

    async with async_session() as session:
        async with session.begin():
            item = await session.get(Info, info_id)
            if not item:
                return {"ok": False, "detail": "Info not found"}

            if title is not None: item.title = title
            if content is not None: item.content = content
            if file and file.filename:
                from previouse.bot.files import upload_file_to_group
                try:
                    file_id, file_name = await upload_file_to_group(await file.read(), file.filename)
                except ValueError as e:
                    return {"ok": False, "detail": str(e)}
                item.file_url = file_id
                item.file_id = file_id
                item.file_name = file_name

    return {"ok": True}


@router.delete("/api/admin/info/{info_id}")
async def admin_delete_info(info_id: int, user=Depends(require_staff)):
    from previouse.db.database import async_session
    from previouse.models.models import Info

    async with async_session() as session:
        async with session.begin():
            item = await session.get(Info, info_id)
            if not item:
                return {"ok": False, "detail": "Info not found"}

            await session.delete(item)

    return {"ok": True}
