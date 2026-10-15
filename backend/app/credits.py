"""Credit ledger operations. Every change has a unique `ref`, so retries never double-charge or double-credit."""
from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .db import CreditEntry, User


class InsufficientCredits(Exception):
    pass


def apply(s: Session, user_id: str, delta: int, reason: str, ref: str) -> bool:
    """Returns False if this ref was already applied. Raises InsufficientCredits on overdraw."""
    if s.scalar(select(CreditEntry.id).where(CreditEntry.ref == ref)):
        return False
    try:
        s.add(CreditEntry(user_id=user_id, delta=delta, reason=reason, ref=ref))
        s.flush()
    except IntegrityError:
        s.rollback()
        return False
    stmt = update(User).where(User.id == user_id).values(credits=User.credits + delta)
    if delta < 0:
        stmt = stmt.where(User.credits >= -delta)
    if s.execute(stmt).rowcount == 0:
        s.rollback()
        raise InsufficientCredits()
    s.commit()
    return True
