from fastapi import APIRouter, Depends, Request

from auth.dependencies import get_current_user
from controllers.passController import get_active_codes, start_pass, stop_pass
from middleware.rate_limit import limiter
from models.user import User

router = APIRouter(prefix="/api/admin/codes")


@router.post("/pass/start")
@limiter.limit("5/minute")
async def start_pass_endpoint(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    body = await request.json()
    mode = body.get("mode", "entry")
    codes = start_pass(mode=mode)
    return {"ok": True, "codes": codes, "mode": mode}


@router.get("/pass/active")
@limiter.limit("60/minute")
async def active_pass_codes(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    codes = get_active_codes()
    return {"ok": True, "codes": codes}


@router.post("/pass/stop")
@limiter.limit("10/minute")
async def stop_pass_endpoint(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    stop_pass()
    return {"ok": True}
