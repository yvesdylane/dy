import logging

from fastapi import APIRouter, Depends, Form, Query, UploadFile

from web.security import verified_tid

logger = logging.getLogger(__name__)
router = APIRouter()


async def notify_interns(title, content, file_id=None, file_name=None):
    from sqlalchemy import select

    from bot.router import application as tg_app
    from db.database import async_session
    from models.models import Role, User

    if not tg_app:
        return

    async with async_session() as session:
        interns = (await session.execute(
            select(User).where(User.role == Role.intern)
        )).scalars().all()

    msg = f"📢 Announcement: {title}\n\n{content}"
    for u in interns:
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
async def admin_list_info(telegram_id: str = Depends(verified_tid)):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import Info, Role, User

    async with async_session() as session:
        user = await session.execute(
            select(User).where(User.telegram_id == telegram_id, User.role.in_([Role.admin, Role.instructor]))
        )
        if not user.scalar_one_or_none():
            return {"ok": False, "detail": "Unauthorized"}

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
    telegram_id: str = Depends(verified_tid),
    title: str = Form(...), content: str = Form(...),
    file: UploadFile = None,
):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import Info, Role, User

    async with async_session() as session:
        async with session.begin():
            user = await session.execute(
                select(User).where(User.telegram_id == telegram_id, User.role.in_([Role.admin, Role.instructor]))
            )
            user = user.scalar_one_or_none()
            if not user:
                return {"ok": False, "detail": "Unauthorized"}

            file_id = None
            file_name = None
            file_url_for_legacy = None
            if file and file.filename:
                from bot.files import upload_file_to_group
                file_id, file_name = await upload_file_to_group(await file.read(), file.filename)
                file_url_for_legacy = file_id

            item = Info(
                title=title, content=content,
                file_url=file_url_for_legacy, file_id=file_id, file_name=file_name,
                created_by=user.id,
            )
            session.add(item)

    await notify_interns(item.title, item.content, file_id, file_name)

    return {"ok": True, "info": {"id": item.id, "title": item.title}}


@router.put("/api/admin/info/{info_id}")
async def admin_update_info(
    info_id: int, telegram_id: str = Depends(verified_tid),
    title: str = Form(None), content: str = Form(None),
    file: UploadFile = None,
):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import Info, Role, User

    async with async_session() as session:
        async with session.begin():
            user = await session.execute(
                select(User).where(User.telegram_id == telegram_id, User.role.in_([Role.admin, Role.instructor]))
            )
            if not user.scalar_one_or_none():
                return {"ok": False, "detail": "Unauthorized"}

            item = await session.get(Info, info_id)
            if not item:
                return {"ok": False, "detail": "Info not found"}

            if title is not None: item.title = title
            if content is not None: item.content = content
            if file and file.filename:
                from bot.files import upload_file_to_group
                file_id, file_name = await upload_file_to_group(await file.read(), file.filename)
                item.file_url = file_id
                item.file_id = file_id
                item.file_name = file_name

    return {"ok": True}


@router.delete("/api/admin/info/{info_id}")
async def admin_delete_info(info_id: int, telegram_id: str = Depends(verified_tid)):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import Info, Role, User

    async with async_session() as session:
        async with session.begin():
            user = await session.execute(
                select(User).where(User.telegram_id == telegram_id, User.role.in_([Role.admin, Role.instructor]))
            )
            if not user.scalar_one_or_none():
                return {"ok": False, "detail": "Unauthorized"}

            item = await session.get(Info, info_id)
            if not item:
                return {"ok": False, "detail": "Info not found"}

            await session.delete(item)

    return {"ok": True}
