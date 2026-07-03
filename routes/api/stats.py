import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from controllers.stats import get_stats
from db.database import get_db

router = APIRouter(prefix="/api/admin")


@router.get("/stats")
async def stats(db: Session = Depends(get_db)):
    loop = asyncio.get_running_loop()
    data = await loop.run_in_executor(None, get_stats, db)
    return data
