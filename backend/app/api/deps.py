from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.session import SESSION_COOKIE_NAME, read_session_token
from app.db.base import get_db
from app.db.models.user import User

__all__ = ["get_db", "get_current_user"]


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    email = read_session_token(token) if token else None
    if email is None:
        raise HTTPException(401, "Not authenticated")

    user = db.scalars(select(User).where(User.email == email)).first()
    if user is None:
        raise HTTPException(401, "Not authenticated")
    return user
