"""Auth + home screen. Dev login only; replace with phone OTP (e.g. MSG91 or Firebase) before launch."""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from .. import credits
from ..config import get_settings
from ..db import Job, Shoot, User, Variation
from ..deps import current_user, get_db

router = APIRouter()


class DevLogin(BaseModel):
    name: str = Field(min_length=1, max_length=120)


@router.post("/auth/dev-login")
def dev_login(body: DevLogin, s=Depends(get_db)):
    settings = get_settings()
    if not settings.dev_mode:
        raise HTTPException(404)
    user = User(name=body.name, token=secrets.token_urlsafe(32), credits=0)
    s.add(user)
    s.commit()
    if settings.free_credits:
        credits.apply(s, user.id, settings.free_credits, "welcome", f"welcome:{user.id}")
    return {"token": user.token, "user_id": user.id}


@router.get("/me")
def me(user: User = Depends(current_user), s=Depends(get_db)):
    s.refresh(user)
    return {"id": user.id, "name": user.name, "credits": user.credits}


@router.get("/shoots")
def recent_shoots(user: User = Depends(current_user), s=Depends(get_db)):
    """Home screen 'Recent shoots'."""
    rows = []
    for shoot in s.scalars(select(Shoot).where(Shoot.user_id == user.id).order_by(Shoot.created_at.desc()).limit(20)):
        job = s.scalar(select(Job).where(Job.shoot_id == shoot.id).order_by(Job.created_at.desc()))
        cover = None
        if job:
            v = s.scalar(select(Variation).where(Variation.job_id == job.id).order_by(Variation.position))
            cover = f"/variations/{v.id}/preview" if v else None
        rows.append({
            "id": shoot.id, "jewellery_type": shoot.jewellery_type, "metal": shoot.metal,
            "latest_job": job and {"id": job.id, "style": job.style, "status": job.status, "count": job.count},
            "cover_url": cover,
        })
    return rows
