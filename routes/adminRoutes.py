from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from models.user import User

router = APIRouter()

PAGES = {
    "dashboard": "admin/sections/dashboard.html",
    "users": "admin/sections/users.html",
    "codes": "admin/sections/codes.html",
    "registers": "admin/sections/registers.html",
    "leaves": "admin/sections/leaves.html",
    "pass": "admin/sections/pass.html",
    "tasks": "admin/sections/tasks.html",
    "cleaning": "admin/sections/cleaning.html",
    "notes": "admin/sections/notes.html",
    "info": "admin/sections/info.html",
    "complaints": "admin/sections/complaints.html",
}


@router.get("/admin", response_class=HTMLResponse)
async def admin_shell(
    request: Request,
    user: User = Depends(get_current_user),
):
    templates = request.app.state.templates
    print(request.session)
    return templates.TemplateResponse(
        request=request, name="admin/index.html", context={"user": user}
    )


@router.get("/admin/page/{page_name}", response_class=HTMLResponse)
async def admin_page(
    request: Request,
    page_name: str,
    user: User = Depends(get_current_user),
):
    template = PAGES.get(page_name)
    if template is None:
        raise HTTPException(status_code=404)
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request, name=template, context={"user": user}
    )
