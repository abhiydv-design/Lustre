"""Guest first, phone sign-in at first save or purchase.

1. App opens          → POST /auth/start            guest account + trial credits, no form
2. Save / download / buy → 403 sign_in_required    app shows the phone screen
3. Phone              → POST /auth/otp/request
4. Code               → POST /auth/otp/verify       (send the guest token: their work is kept)
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select, update

from .. import credits
from ..config import get_settings
from ..db import CreditEntry, Generation, OtpCode, Product, Report, User, now
from ..deps import current_user, get_db, optional_user
from ..sms import get_sms

router = APIRouter()

OTP_TTL = timedelta(minutes=10)
OTP_MAX_ATTEMPTS = 5
OTP_MAX_SENDS = 3  # per phone per 10 minutes


def _hash(*parts: str) -> str:
    return hmac.new(get_settings().secret_key.encode(), "|".join(parts).encode(), hashlib.sha256).hexdigest()


def normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if not re.fullmatch(r"[6-9]\d{9}", digits):
        raise HTTPException(422, {"code": "invalid_phone", "message": "Enter a 10-digit Indian mobile number."})
    return "+91" + digits


def _trial_ref(phone: str) -> str:
    """Trial credits are given once per phone number, ever. The ref stores a hash, not the number."""
    return f"trial:phone:{_hash('trial', phone)[:32]}"


@router.post("/auth/start")
def start(s=Depends(get_db)):
    """Instant guest account with trial credits. Guests can generate and review, not save or buy."""
    user = User(token=secrets.token_urlsafe(32))
    s.add(user)
    s.commit()
    n = get_settings().trial_credits
    if n:
        credits.apply(s, user.id, n, "trial", f"trial:guest:{user.id}", note="Free trial")
    return {"token": user.token, "user_id": user.id, "credits": n, "guest": True}


class OtpRequest(BaseModel):
    phone: str


@router.post("/auth/otp/request")
def otp_request(body: OtpRequest, s=Depends(get_db)):
    settings = get_settings()
    phone = normalize_phone(body.phone)
    recent = s.scalar(select(func.count(OtpCode.id)).where(OtpCode.phone == phone,
                                                          OtpCode.created_at >= now() - OTP_TTL))
    if recent >= OTP_MAX_SENDS:
        raise HTTPException(429, {"code": "too_many_codes", "message": "Too many codes sent. Try again in a few minutes."})
    code = f"{secrets.randbelow(10**6):06d}"
    s.add(OtpCode(phone=phone, code_hash=_hash(phone, code), expires_at=now() + OTP_TTL))
    s.commit()
    get_sms(settings.sms_provider).send(phone, f"{code} is your {settings.brand_name} sign-in code.")
    out = {"sent": True, "phone": phone}
    if settings.dev_mode:
        out["dev_code"] = code
    return out


class OtpVerify(BaseModel):
    phone: str
    code: str


def _merge_guest_into(s, guest: User, target: User) -> None:
    """Move a guest's products, images and reports into an existing account.
    Credits don't move: a guest's balance is only trial credits, and that phone already had its trial."""
    s.execute(update(Product).where(Product.user_id == guest.id).values(user_id=target.id))
    s.execute(update(Generation).where(Generation.user_id == guest.id).values(user_id=target.id))
    s.execute(update(Report).where(Report.user_id == guest.id).values(user_id=target.id))
    guest.token = "merged:" + secrets.token_urlsafe(24)
    guest.credits = 0
    s.commit()


@router.post("/auth/otp/verify")
def otp_verify(body: OtpVerify, current: User | None = Depends(optional_user), s=Depends(get_db)):
    phone = normalize_phone(body.phone)
    otp = s.scalar(select(OtpCode).where(OtpCode.phone == phone, OtpCode.used.is_(False))
                   .order_by(OtpCode.created_at.desc()))
    expires = otp and (otp.expires_at if otp.expires_at.tzinfo else otp.expires_at.replace(tzinfo=now().tzinfo))
    if not otp or expires < now() or otp.attempts >= OTP_MAX_ATTEMPTS:
        raise HTTPException(400, {"code": "code_expired", "message": "That code has expired. Request a new one."})
    otp.attempts += 1
    if not hmac.compare_digest(otp.code_hash, _hash(phone, body.code.strip())):
        s.commit()
        raise HTTPException(400, {"code": "wrong_code", "message": "That code isn't right. Please check and try again."})
    otp.used = True
    s.commit()

    existing = s.scalar(select(User).where(User.phone == phone))
    trial = get_settings().trial_credits
    if existing:
        if current and current.is_guest and current.id != existing.id:
            _merge_guest_into(s, current, existing)
        user = existing
    elif current and current.is_guest:
        current.phone = phone  # the guest account becomes the real account; nothing moves
        s.commit()
        user = current
        if not credits.apply(s, user.id, 0, "trial_claim", _trial_ref(phone)):
            # This phone already used its trial (e.g. on a deleted account): take back unused guest trial.
            if user.credits:
                credits.apply(s, user.id, -user.credits, "trial_reused", f"trial-reused:{user.id}",
                              note="This number already used its free trial")
    else:
        user = User(phone=phone, token=secrets.token_urlsafe(32))
        s.add(user)
        s.commit()
        if trial:
            credits.apply(s, user.id, trial, "trial", _trial_ref(phone), note="Free trial")
    s.refresh(user)
    return {"token": user.token, "user_id": user.id, "credits": user.credits, "guest": False}


@router.get("/me")
def me(user: User = Depends(current_user), s=Depends(get_db)):
    s.refresh(user)
    return {"id": user.id, "guest": user.is_guest, "phone": user.phone, "credits": user.credits}


@router.get("/me/credits")
def credit_history(user: User = Depends(current_user), s=Depends(get_db)):
    """Balance and every transaction, newest first (spec §9.7)."""
    s.refresh(user)
    entries = s.scalars(select(CreditEntry).where(CreditEntry.user_id == user.id, CreditEntry.delta != 0)
                        .order_by(CreditEntry.id.desc()).limit(200))
    return {"balance": user.credits, "transactions": [
        {"delta": e.delta, "reason": e.reason, "note": e.note, "at": e.created_at.isoformat()} for e in entries]}


@router.delete("/me", status_code=204)
def delete_account(user: User = Depends(current_user), s=Depends(get_db)):
    """Deletes every product, photo and image and their files now. Payment and credit records are
    kept without personal details, for accounting. See docs/data-retention.md."""
    from .products import delete_product_everything
    for pid in list(s.scalars(select(Product.id).where(Product.user_id == user.id))):
        delete_product_everything(s, pid)
    s.query(Report).filter(Report.user_id == user.id).delete()
    user.phone = None
    user.name = ""
    user.token = "deleted:" + secrets.token_urlsafe(24)
    user.credits = 0
    s.commit()
