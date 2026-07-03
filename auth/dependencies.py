import asyncio

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from controllers.userController import get_user
from db.database import get_db
from models.user import User


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    user_id = request.session.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    loop = asyncio.get_running_loop()
    user = await loop.run_in_executor(None, get_user, db, user_id)

    if user is None:
        request.session.clear()
        raise HTTPException(status_code=401, detail="User not found")

    return user
