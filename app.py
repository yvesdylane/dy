import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.sessions import SessionMiddleware

from config import settings
from cronjobs.scheduler import start_scheduler, stop_scheduler
from middleware.rate_limit import limiter
from db.database import init_db, close_db
from bot.router import init_bot, shutdown_bot, process_update, application
from bot.commands import handlers
from routes import auth as auth_routes
from routes import web as web_routes
from routes.adminRoutes import router as admin_router
from routes.api.stats import router as stats_api_router
from routes.api.users import router as users_api_router
from routes.api.codes import router as codes_api_router
from routes.api.photos import router as photos_api_router
from routes.api.attendance import router as attendance_api_router
from routes.api.leaves import router as leaves_api_router
from routes.api.pass_codes import router as pass_api_router
from routes.api.tasks import router as tasks_api_router
from routes.api.notes import router as notes_api_router
from routes.api.info import router as info_api_router
from routes.api.face import router as face_api_router
from routes.api.complaints import router as complaints_api_router
from routes.api.evaluations import router as evaluations_api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, init_db)
    await init_bot(handlers)
    bot = application.bot if application else None
    app.state.bot = bot
    start_scheduler(bot)
    logger.info("Application started")
    yield
    stop_scheduler()
    await shutdown_bot()
    await loop.run_in_executor(None, close_db)
    logger.info("Application shut down")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    max_age=1800,
    same_site="none",
    https_only=True,
)

app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.mount("/static", StaticFiles(directory="web/static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

templates = Jinja2Templates(directory="web/templates")
app.state.templates = templates

app.include_router(web_routes.router)
app.include_router(admin_router)
app.include_router(auth_routes.router)
app.include_router(stats_api_router)
app.include_router(users_api_router)
app.include_router(codes_api_router)
app.include_router(photos_api_router)
app.include_router(attendance_api_router)
app.include_router(leaves_api_router)
app.include_router(pass_api_router)
app.include_router(tasks_api_router)
app.include_router(notes_api_router)
app.include_router(info_api_router)
app.include_router(face_api_router)
app.include_router(complaints_api_router)
app.include_router(evaluations_api_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()
    msg_text = (
        data.get("message", {}).get("text")
        or data.get("message", {}).get("caption")
        or data.get("edited_message", {}).get("text")
        or "(non-text)"
    )
    await process_update(data)
    logger.info("MSG: %s \u2192 OK", msg_text)
    return {"ok": True}
