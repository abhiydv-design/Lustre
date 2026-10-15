"""One code path for every way a photo gets paid for: single download, download all,
and 'buy credits then finish my download'."""
from __future__ import annotations

from sqlalchemy.orm import Session

from . import credits
from .db import Job, User, Variation


def owned_variations(s: Session, user_id: str, ids: list[str]) -> list[Variation]:
    out = []
    for vid in dict.fromkeys(ids):
        v = s.get(Variation, vid)
        if not v or s.get(Job, v.job_id).user_id != user_id:
            raise LookupError(vid)
        out.append(v)
    return out


def pay_and_queue(s: Session, user_id: str, ids: list[str]) -> list[str]:
    """Charge 1 credit per not-yet-paid photo (all or nothing), return ids that still need a 4K render."""
    variations = owned_variations(s, user_id, ids)
    unpaid = [v for v in variations if not v.paid]
    balance = s.get(User, user_id).credits
    if balance < len(unpaid):
        raise credits.InsufficientCredits(needed=len(unpaid) - balance, balance=balance)
    for v in unpaid:
        v.charges += 1
        v.paid = True
        credits.apply(s, user_id, -1, "download", f"download:{v.id}:{v.charges}")  # commits
    to_render = []
    for v in owned_variations(s, user_id, ids):
        if v.final_status in ("none", "failed"):
            v.final_status = "rendering"
            to_render.append(v.id)
    s.commit()
    return to_render
