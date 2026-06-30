import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from config import settings
from db.database import init_db, close_db
from routes import auth as auth_routes
from routes import web as web_routes

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

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    max_age=1800,
    same_site="lax",
    https_only=False,
)

app.mount("/static", StaticFiles(directory="web/static"), name="static")

templates = Jinja2Templates(directory="web/templates")
app.state.templates = templates

app.include_router(web_routes.router)
app.include_router(auth_routes.router)
