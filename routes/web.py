from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from auth.dependencies import get_current_user

router = APIRouter()

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
