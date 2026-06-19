import logging

from fastapi import APIRouter, Depends, Form, Query, UploadFile

from web.security import verified_tid

logger = logging.getLogger(__name__)
router = APIRouter()


async def notify_interns(department, title, content, file_id=None, file_name=None):
    from sqlalchemy import select

    from bot.router import application as tg_app
    from db.database import async_session
    from models.models import Role, User

    if not tg_app:
        return

    async with async_session() as session:
        interns = (await session.execute(
            select(User).where(User.role == Role.intern, User.department == department)
        )).scalars().all()

    msg = f"📝 New Note: {title}\n\n{content}\n\nDepartment: {department.value}"
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


@router.get("/api/admin/notes")
async def admin_list_notes(telegram_id: str = Depends(verified_tid), department: str | None = Query(None)):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import Department, Note, Role, User

    async with async_session() as session:
        user = await session.execute(
            select(User).where(User.telegram_id == telegram_id, User.role.in_([Role.admin, Role.instructor]))
        )
        if not user.scalar_one_or_none():
            return {"ok": False, "detail": "Unauthorized"}

        stmt = select(Note).order_by(Note.created_at.desc())
        if department:
            stmt = stmt.where(Note.department == Department(department))

        notes = (await session.execute(stmt)).scalars().all()

    return {"ok": True, "notes": [{
        "id": n.id, "title": n.title, "content": n.content,
        "file_url": n.file_id or n.file_url,
        "file_id": n.file_id,
        "file_name": n.file_name,
        "department": n.department.value if n.department else None,
        "uploaded_by": n.uploaded_by,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    } for n in notes]}


@router.post("/api/admin/notes")
async def admin_create_note(
    telegram_id: str = Depends(verified_tid),
    title: str = Form(...), content: str = Form(...),
    department: str | None = Form(None), file: UploadFile = None,
):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import Department, Note, Role, User

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

            note = Note(
                title=title, content=content,
                file_url=file_url_for_legacy, file_id=file_id, file_name=file_name,
                department=Department(department) if department else None, uploaded_by=user.id,
            )
            session.add(note)

    note_department = Department(department) if department else None
    if note_department:
        await notify_interns(note_department, note.title, note.content, file_id, file_name)

    return {"ok": True, "note": {"id": note.id, "title": note.title,
                                 "department": note.department.value if note.department else None}}


@router.put("/api/admin/notes/{note_id}")
async def admin_update_note(
    note_id: int, telegram_id: str = Depends(verified_tid),
    title: str = Form(None), content: str = Form(None),
    department: str = Form(None), file: UploadFile = None,
):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import Department, Note, Role, User

    async with async_session() as session:
        async with session.begin():
            user = await session.execute(
                select(User).where(User.telegram_id == telegram_id, User.role.in_([Role.admin, Role.instructor]))
            )
            if not user.scalar_one_or_none():
                return {"ok": False, "detail": "Unauthorized"}

            note = await session.get(Note, note_id)
            if not note:
                return {"ok": False, "detail": "Note not found"}

            if title is not None: note.title = title
            if content is not None: note.content = content
            if department is not None: note.department = Department(department) if department else None
            if file and file.filename:
                from bot.files import upload_file_to_group
                file_id, file_name = await upload_file_to_group(await file.read(), file.filename)
                note.file_url = file_id
                note.file_id = file_id
                note.file_name = file_name

    return {"ok": True}


@router.delete("/api/admin/notes/{note_id}")
async def admin_delete_note(note_id: int, telegram_id: str = Depends(verified_tid)):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import Note, Role, User

    async with async_session() as session:
        async with session.begin():
            user = await session.execute(
                select(User).where(User.telegram_id == telegram_id, User.role.in_([Role.admin, Role.instructor]))
            )
            if not user.scalar_one_or_none():
                return {"ok": False, "detail": "Unauthorized"}

            note = await session.get(Note, note_id)
            if not note:
                return {"ok": False, "detail": "Note not found"}

            await session.delete(note)

    return {"ok": True}
