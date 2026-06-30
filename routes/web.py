from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from db.database import get_db
from models.user import User

router = APIRouter()

ROLE_PATHS = {
    "admin": "/admin",
    "super_admin": "/admin",
    "instructor": "/instructor",
}


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    role = request.session.get("role")
    if role:
        path = ROLE_PATHS.get(role)
        if path:
            return RedirectResponse(url=path)
    templates = request.app.state.templates
    return templates.TemplateResponse(request=request, name="index.html")


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse(request=request, name="registraion.html")


@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    user: User = Depends(get_current_user),
):
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request, name="admin/index.html", context={"user": user}
    )


@router.get("/instructor", response_class=HTMLResponse)
async def instructor_dashboard(
    request: Request,
    user: User = Depends(get_current_user),
):
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request, name="instructor/index.html", context={"user": user}
    )
