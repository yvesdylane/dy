import logging

from fastapi import APIRouter, Depends, Form, Query, UploadFile

from previouse.web.security import require_staff

logger = logging.getLogger(__name__)
router = APIRouter()


async def notify_interns(department, title, content, file_id=None, file_name=None):
    from sqlalchemy import select

    from previouse.bot.router import application as tg_app
    from previouse.db.database import async_session
    from previouse.models.models import Role, User

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
async def admin_list_notes(user=Depends(require_staff), department: str | None = Query(None)):
    from sqlalchemy import select

    from previouse.db.database import async_session
    from previouse.models.models import Department, Note

    async with async_session() as session:
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
    staff_user=Depends(require_staff),
    title: str = Form(...), content: str = Form(...),
    department: str | None = Form(None), file: UploadFile = None,
):
    from previouse.db.database import async_session
    from previouse.models.models import Department, Note

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

            note = Note(
                title=title, content=content,
                file_url=file_url_for_legacy, file_id=file_id, file_name=file_name,
                department=Department(department) if department else None, uploaded_by=staff_user.id,
            )
            session.add(note)

    note_department = Department(department) if department else None
    if note_department:
        await notify_interns(note_department, note.title, note.content, file_id, file_name)

    return {"ok": True, "note": {"id": note.id, "title": note.title,
                                 "department": note.department.value if note.department else None}}


@router.put("/api/admin/notes/{note_id}")
async def admin_update_note(
    note_id: int, user=Depends(require_staff),
    title: str = Form(None), content: str = Form(None),
    department: str = Form(None), file: UploadFile = None,
):
    from previouse.db.database import async_session
    from previouse.models.models import Department, Note

    async with async_session() as session:
        async with session.begin():
            note = await session.get(Note, note_id)
            if not note:
                return {"ok": False, "detail": "Note not found"}

            if title is not None: note.title = title
            if content is not None: note.content = content
            if department is not None: note.department = Department(department) if department else None
            if file and file.filename:
                from previouse.bot.files import upload_file_to_group
                try:
                    file_id, file_name = await upload_file_to_group(await file.read(), file.filename)
                except ValueError as e:
                    return {"ok": False, "detail": str(e)}
                note.file_url = file_id
                note.file_id = file_id
                note.file_name = file_name

    return {"ok": True}


@router.delete("/api/admin/notes/{note_id}")
async def admin_delete_note(note_id: int, user=Depends(require_staff)):
    from previouse.db.database import async_session
    from previouse.models.models import Note

    async with async_session() as session:
        async with session.begin():
            note = await session.get(Note, note_id)
            if not note:
                return {"ok": False, "detail": "Note not found"}

            await session.delete(note)

    return {"ok": True}
