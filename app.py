import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from db.database import close_db, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
        logger.info("Application started")
    except Exception as e:
        logger.error(f"Startup failed: %s", e)
    yield
    try:
        await close_db()
        logger.info("Application shut down cleanly")
    except Exception as e:
        logger.error(f"Shutdown error: %s", e)


app = FastAPI(title="dy", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}
