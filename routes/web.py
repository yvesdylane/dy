from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from auth.dependencies import get_current_user
from models.enums import Role
from models.user import User

router = APIRouter()

INSTRUCTOR_PAGES = {
    "dashboard": "instructor/sections/dashboard.html",
    "tasks": "instructor/sections/tasks.html",
    "registers": "admin/sections/registers.html",
    "leaves": "admin/sections/registers.html",
    "pass": "admin/sections/registers.html",
    "evaluations": "admin/sections/evaluations.html",
}

ROLE_PATHS = {
    "admin": "/admin",
    "super_admin": "/admin",
    "instructor": "/instructor",
}


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    print(request.session)
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


@router.get("/instructor", response_class=HTMLResponse)
async def instructor_dashboard(
    request: Request,
    user=Depends(get_current_user),
):
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request, name="instructor/index.html", context={"user": user}
    )


@router.get("/instructor/page/{page_name}", response_class=HTMLResponse)
async def instructor_page(
    request: Request,
    page_name: str,
    user: User = Depends(get_current_user),
):
    if user.role != Role.instructor:
        raise HTTPException(status_code=403, detail="Instructor only")
    template = INSTRUCTOR_PAGES.get(page_name)
    if template is None:
        raise HTTPException(status_code=404, detail="Page not found")
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request, name=template, context={"user": user}
    )
