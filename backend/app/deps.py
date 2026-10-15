from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select

from .db import User, new_session


def get_db():
    s = new_session()
    try:
        yield s
    finally:
        s.close()


def current_user(authorization: str | None = Header(default=None), s=Depends(get_db)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing bearer token")
    user = s.scalar(select(User).where(User.token == authorization.split(" ", 1)[1].strip()))
    if not user:
        raise HTTPException(401, "Invalid token")
    return user
