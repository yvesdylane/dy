import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from bot.router import init_bot, process_update, shutdown_bot
from db.database import close_db, init_db
from web.routes import router as web_router
from web.attendance_routes import router as attendance_router
from web.task_routes import router as task_router
from web.note_routes import router as note_router
from web.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
        await init_bot()
        start_scheduler()
        logger.info("Application started")
    except Exception as e:
        logger.error("Startup failed: %s", e)
    yield
    try:
        stop_scheduler()
        await shutdown_bot()
        await close_db()
        logger.info("Application shut down cleanly")
    except Exception as e:
        logger.error("Shutdown error: %s", e)


app = FastAPI(title="dy", lifespan=lifespan)
app.include_router(web_router)
app.include_router(attendance_router)
app.include_router(task_router)
app.include_router(note_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()
    print(data)
    await process_update(data)
    return {"ok": True}
