import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from auth.telegram import verify_init_data
from db.database import init_db, close_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, init_db)
    logger.info("Application started")
    yield
    await loop.run_in_executor(None, close_db)
    logger.info("Application shut down")


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="web/static"), name="static")

templates = Jinja2Templates(directory="web/templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@app.post("/auth/telegram")
async def telegram_auth(data: dict = Body(...)):

    telegram_user = verify_init_data(
        data["initData"]
    )

    print(telegram_user)

    return {
        "success": True,
        "telegram_id": telegram_user.id,
        "username": telegram_user.username,
    }