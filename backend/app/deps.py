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


def optional_user(authorization: str | None = Header(default=None), s=Depends(get_db)) -> User | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return s.scalar(select(User).where(User.token == authorization.split(" ", 1)[1].strip()))


def current_user(user: User | None = Depends(optional_user)) -> User:
    if not user:
        raise HTTPException(401, "Missing or invalid token")
    return user


def signed_in_user(user: User = Depends(current_user)) -> User:
    """Saving, downloading and buying need a phone sign-in; everything else works as a guest."""
    if user.is_guest:
        raise HTTPException(403, {"code": "sign_in_required",
                                  "message": "Sign in with your phone number to save your photos and buy credits."})
    return user
