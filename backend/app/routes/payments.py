"""Screen 6: credit packs via Razorpay (UPI, cards, net banking)."""
from __future__ import annotations

import hashlib
import hmac
import json

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from .. import credits
from ..config import get_settings
from ..db import Payment, User
from ..deps import current_user, get_db
from ..downloads import owned_variations, pay_and_queue
from ..pipeline.run import process_final

router = APIRouter()

PACKS = {"starter": 10, "shop": 50, "studio": 200}


@router.get("/credits/packs")
def packs():
    prices = get_settings().pack_prices_inr
    return [{"id": k, "credits": c, "price_inr": prices.get(k)} for k, c in PACKS.items()]


class OrderRequest(BaseModel):
    pack: str
    then_download: list[str] = []  # photos to deliver automatically once payment lands


@router.post("/payments/orders", status_code=201)
def create_order(body: OrderRequest, user: User = Depends(current_user), s=Depends(get_db)):
    settings = get_settings()
    if body.pack not in PACKS:
        raise HTTPException(422, "Unknown pack")
    price = settings.pack_prices_inr.get(body.pack)
    if not price:
        raise HTTPException(503, f"Price for '{body.pack}' is not configured")
    try:
        owned_variations(s, user.id, body.then_download)
    except LookupError:
        raise HTTPException(404, "Photo not found")
    payment = Payment(user_id=user.id, pack=body.pack, credits=PACKS[body.pack], amount_paise=price * 100,
                      then_download=json.dumps(body.then_download))
    s.add(payment)
    s.flush()
    if settings.razorpay_key_id and settings.razorpay_key_secret:
        r = httpx.post("https://api.razorpay.com/v1/orders",
                       auth=(settings.razorpay_key_id, settings.razorpay_key_secret), timeout=20,
                       json={"amount": payment.amount_paise, "currency": "INR", "receipt": payment.id,
                             "notes": {"user_id": user.id, "pack": body.pack}})
        if r.status_code >= 300:
            s.rollback()
            raise HTTPException(502, "Payment provider error")
        payment.order_id = r.json()["id"]
    elif settings.dev_mode:
        payment.order_id = f"order_mock_{payment.id}"
    else:
        raise HTTPException(503, "Payments are not configured")
    s.commit()
    # The app opens Razorpay Checkout with these values.
    return {"order_id": payment.order_id, "amount": payment.amount_paise, "currency": "INR",
            "key_id": settings.razorpay_key_id, "credits": payment.credits}


def _fulfil(s, order_id: str, tasks: BackgroundTasks) -> bool:
    payment = s.scalar(select(Payment).where(Payment.order_id == order_id))
    if not payment:
        return False
    first_time = credits.apply(s, payment.user_id, payment.credits, "purchase", f"payment:{order_id}")
    payment = s.scalar(select(Payment).where(Payment.order_id == order_id))
    payment.status = "paid"
    s.commit()
    pending = json.loads(payment.then_download or "[]")
    if first_time and pending:
        # Finish what the jeweller was doing when they ran out: no second tap needed.
        try:
            for vid in pay_and_queue(s, payment.user_id, pending):
                tasks.add_task(process_final, vid)
        except (credits.InsufficientCredits, LookupError):
            pass  # credits are in their account either way; they can tap download
    return True


@router.post("/payments/webhook")
async def razorpay_webhook(request: Request, tasks: BackgroundTasks, s=Depends(get_db)):
    """Credits are only ever added here (server-to-server), never from the app's word."""
    secret = get_settings().razorpay_webhook_secret
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not secret:
        raise HTTPException(503, "Webhook secret not configured")
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(400, "Bad signature")
    event = json.loads(body)
    if event.get("event") in ("order.paid", "payment.captured"):
        order_id = event["payload"]["payment"]["entity"].get("order_id")
        if order_id:
            _fulfil(s, order_id, tasks)
    return {"ok": True}


@router.post("/payments/mock-complete/{order_id}")
def mock_complete(order_id: str, tasks: BackgroundTasks, user: User = Depends(current_user), s=Depends(get_db)):
    if not get_settings().dev_mode or not order_id.startswith("order_mock_"):
        raise HTTPException(404)
    if not _fulfil(s, order_id, tasks):
        raise HTTPException(404, "Order not found")
    return {"ok": True}
