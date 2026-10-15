"""Spec §16 metrics, computed from the database for a time window.

Every rate returns None when there's nothing to divide by, rather than a misleading 0%.
Critical/major fidelity error rates come from the evaluation harness (reviewed by people),
not from production, so they are not here.
"""
from __future__ import annotations

import json
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db import CreditEntry, Event, Generation, Payment, Product, Report, SourcePhoto, User, now


def _aware(dt: datetime | None) -> datetime | None:
    return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _rate(n: int, d: int) -> float | None:
    return round(n / d, 4) if d else None


def _median_minutes(deltas: list[timedelta]) -> float | None:
    return round(statistics.median(d.total_seconds() / 60 for d in deltas), 1) if deltas else None


def compute(s: Session, days: int = 30) -> dict:
    since = now() - timedelta(days=days)
    real_user = ~User.token.like("merged:%")  # merged guests are duplicates of a real account

    users = list(s.scalars(select(User).where(real_user, User.created_at >= since)))
    user_ids = {u.id for u in users}
    created = {u.id: _aware(u.created_at) for u in users}

    gens = list(s.scalars(select(Generation).where(Generation.created_at >= since)))
    done = [g for g in gens if g.status == "done"]
    failed = [g for g in gens if g.status == "failed"]
    done_ids = {g.id for g in done}
    accepted = [g for g in done if g.review == "accepted"]

    # ---------- §16.1 usage ----------
    first_upload = dict(s.execute(
        select(Product.user_id, func.min(SourcePhoto.created_at))
        .join(SourcePhoto, SourcePhoto.product_id == Product.id).group_by(Product.user_id)).all())
    first_result = dict(s.execute(
        select(Generation.user_id, func.min(Generation.finished_at))
        .where(Generation.status == "done").group_by(Generation.user_id)).all())
    to_upload = [_aware(first_upload[u]) - created[u] for u in user_ids if first_upload.get(u)]
    to_result = [_aware(first_result[u]) - created[u] for u in user_ids if first_result.get(u)]

    products_with_photos = set(s.scalars(
        select(SourcePhoto.product_id).join(Product, Product.id == SourcePhoto.product_id)
        .where(Product.created_at >= since).distinct()))
    gen_by_product = defaultdict(list)
    for g in gens:
        if g.status != "failed":
            gen_by_product[g.product_id].append(g)
    converted = products_with_photos & set(gen_by_product)
    repeat_days = sum(1 for gs in gen_by_product.values()
                      if len({_aware(g.created_at).date() for g in gs}) >= 2)

    events = list(s.scalars(select(Event).where(Event.created_at >= since)))
    downloaded = {e.generation_id for e in events if e.type == "download"} & done_ids
    shared = {e.generation_id for e in events if e.type == "share"} & done_ids
    share_channels = defaultdict(int)
    for e in events:
        if e.type == "share":
            share_channels[e.channel or "other"] += 1
    active = {g.user_id for g in gens}

    usage = {
        "new_accounts": len(users),
        "median_minutes_account_to_first_upload": _median_minutes(to_upload),
        "upload_to_generation_conversion": _rate(len(converted), len(products_with_photos)),
        "median_minutes_to_first_result": _median_minutes(to_result),
        "accepted_image_rate": _rate(len(accepted), len(done)),
        "download_rate": _rate(len(downloaded), len(done)),
        "share_rate": _rate(len(shared), len(done)),
        "shares_by_channel": dict(share_channels),
        "repeat_generation_rate": _rate(sum(1 for gs in gen_by_product.values() if len(gs) >= 2), len(gen_by_product)),
        "products_per_active_user": _rate(len(gen_by_product), len(active)),
        "accepted_images_per_active_user": _rate(len(accepted), len(active)),
        "products_reused_on_another_day": _rate(repeat_days, len(gen_by_product)),
    }

    # ---------- §16.2 quality ----------
    reports = list(s.scalars(select(Report).where(Report.created_at >= since)))
    detail_reported = {r.generation_id for r in reports if r.kind == "product_detail"}
    visual_reported = {r.generation_id for r in reports if r.kind == "visual_quality"}
    refunded_quality = s.scalar(select(func.count(CreditEntry.id)).where(
        CreditEntry.reason == "refund_quality", CreditEntry.created_at >= since))
    judged = [g for g in done if g.review in ("accepted", "reported")]

    products = {p.id: p for p in s.scalars(select(Product).where(Product.id.in_({g.product_id for g in gens})))}
    photos = {p.id: p for p in s.scalars(select(SourcePhoto).where(SourcePhoto.id.in_({g.photo_id for g in gens if g.photo_id})))}

    def photo_condition(g: Generation) -> str:
        ph = photos.get(g.photo_id)
        if not ph:
            return "unknown"
        hints = " ".join(json.loads(ph.hints or "[]")).lower()
        for word, label in (("blurry", "blurry"), ("dark", "dark"), ("small", "small"), ("edge", "cropped")):
            if word in hints:
                return label
        return "clean photo"

    def breakdown(key) -> dict:
        groups = defaultdict(list)
        for g in gens:
            groups[key(g) or "unknown"].append(g)
        out = {}
        for k, gs in sorted(groups.items()):
            d = [g for g in gs if g.status == "done"]
            out[k] = {"generations": len(gs), "done": len(d),
                      "accepted_rate": _rate(sum(g.review == "accepted" for g in d), len(d)),
                      "detail_complaint_rate": _rate(sum(g.id in detail_reported for g in d), len(d)),
                      "technical_failure_rate": _rate(sum(g.status == "failed" for g in gs), len(gs))}
        return out

    quality = {
        "generations": len(gens), "done": len(done), "failed": len(failed),
        "product_detail_complaint_rate": _rate(len(detail_reported & done_ids), len(done)),
        "visual_quality_complaint_rate": _rate(len(visual_reported & done_ids), len(done)),
        "technical_failure_rate": _rate(len(failed), len(gens)),
        "quality_refund_rate": _rate(refunded_quality, len(done)),
        "user_judged_usable_rate": _rate(sum(g.review == "accepted" for g in judged), len(judged)),
        "reports_waiting_for_review": s.scalar(select(func.count(Report.id)).where(Report.refund == "under_review")),
        "by_category": breakdown(lambda g: products[g.product_id].category if g.product_id in products else None),
        "by_material": breakdown(lambda g: products[g.product_id].metal if g.product_id in products else None),
        "by_preset": breakdown(lambda g: g.preset),
        "by_photo_condition": breakdown(photo_condition),
    }

    # ---------- §16.3 business ----------
    all_real = s.scalar(select(func.count(User.id)).where(real_user, User.created_at >= since))
    activated = {g.user_id for g in gens} & user_ids
    paid = list(s.scalars(select(Payment).where(Payment.status == "paid", Payment.created_at >= since)))
    payers = defaultdict(int)
    for p in paid:
        payers[p.user_id] += 1
    revenue = sum(p.amount_paise for p in paid) / 100
    cost = sum(g.provider_cost_inr or 0 for g in gens)
    business = {
        "trial_activation_rate": _rate(len(activated), all_real),
        "trial_to_purchase_conversion": _rate(len(set(payers) & activated), len(activated)),
        "paying_accounts": len(payers),
        "repeat_purchase_rate": _rate(sum(1 for n in payers.values() if n >= 2), len(payers)),
        "revenue_inr": round(revenue, 2),
        "revenue_per_paying_account_inr": round(revenue / len(payers), 2) if payers else None,
        "estimated_provider_cost_inr": round(cost, 2),
        "cost_per_generated_image_inr": round(cost / len(done), 2) if done else None,
        "cost_per_accepted_image_inr": round(cost / len(accepted), 2) if accepted else None,
        "cost_note": "Estimated from COST_PER_SCENE_INR and COST_PER_UPSCALE_INR; failed generations count toward cost.",
    }
    return {"window_days": days, "generated_at": now().isoformat(),
            "usage": usage, "quality": quality, "business": business}
