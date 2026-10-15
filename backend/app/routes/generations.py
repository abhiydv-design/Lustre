"""Generate (§9.4), review and report (§9.5), download (§9.6), refunds (§12.3)."""
from __future__ import annotations

import io
from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
from PIL import Image
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from .. import credits, storage
from ..config import get_settings
from ..db import CreditEntry, Generation, Product, Report, SourcePhoto, User, now
from ..deps import current_user, get_db, signed_in_user
from ..pipeline.composite import watermark
from ..pipeline.geometry import ASPECTS
from ..pipeline.marketplaces import verified as verified_marketplaces
from ..pipeline.run import process_generation
from ..pipeline.styles import STYLES
from .products import CATEGORIES, METALS, delete_generation_files, generation_summary, own_product

router = APIRouter()

DETAIL_ISSUES = {
    "stones": "Stone count or placement changed",
    "stone_look": "Stone shape or colour changed",
    "setting": "Prongs, bezel, or setting changed",
    "metal": "Metal colour or finish changed",
    "chain_clasp": "Chain links or clasp changed",
    "shape": "Shape or proportions changed",
    "marking": "Engraving, logo, or identifying mark changed",
    "other_detail": "Other product detail changed",
}
QUALITY_ISSUES = {
    "blurry": "Blurry or low detail",
    "framing": "Poor crop or framing",
    "shadow": "Unnatural shadow or reflection",
    "background": "Background artefact",
    "defect": "Unwanted object or visual defect",
    "other_quality": "Other quality issue",
}
STAGES = [("cutout", "Cutting out your piece"), ("scene", "Building the background"),
          ("lighting", "Matching light and shadow"), ("upscale", "Making the full-size image"),
          ("ready", "Ready")]


@router.get("/catalog")
def catalog():
    """Everything the Choose-a-look screen needs, in English and Hindi."""
    s = get_settings()
    return {
        "categories": [{"id": k, "label": en, "label_hi": hi} for k, (en, hi) in CATEGORIES.items()],
        "metals": METALS,
        "outputs": [{"id": "catalogue", "available": True},
                    {"id": "marketplace", "available": bool(verified_marketplaces())}],
        "presets": [{"id": st.id, "label": st.label, "label_hi": st.label_hi, "available": st.available,
                     "group": st.group} for st in STYLES.values()],
        "aspect_ratios": [{"id": k, "width": w, "height": h} for k, (w, h) in ASPECTS.items()],
        "marketplace_presets": [{"id": m.id, "marketplace": m.marketplace, "slot": m.slot,
                                 "width": m.width, "height": m.height, "verified_on": m.verified_on}
                                for m in verified_marketplaces().values()],
        "costs": {"first_image": s.initial_generation_cost, "additional_image": s.additional_generation_cost},
        "report_categories": {"product_detail": DETAIL_ISSUES, "visual_quality": QUALITY_ISSUES},
    }


def _cost(s, product_id: str) -> tuple[int, bool]:
    """First image of a product vs. additional variations; failed generations don't count."""
    settings = get_settings()
    prior = s.scalar(select(func.count(Generation.id)).where(
        Generation.product_id == product_id, Generation.status != "failed"))
    return (settings.additional_generation_cost, True) if prior else (settings.initial_generation_cost, False)


def needs_credits(user: User, needed: int) -> HTTPException:
    from .payments import packs
    return HTTPException(402, {"code": "needs_credits", "needed": needed, "balance": user.credits,
                               "sign_in_required_to_buy": user.is_guest, "packs": packs()})


@router.get("/products/{product_id}/quote")
def quote(product_id: str, user: User = Depends(current_user), s=Depends(get_db)):
    """Shown before the Generate button (§4.5: costs visible before generation)."""
    own_product(s, user, product_id)
    cost, additional = _cost(s, product_id)
    s.refresh(user)
    return {"cost": cost, "additional": additional, "balance": user.credits,
            "enough": user.credits >= cost}


class GenerateIn(BaseModel):
    output: str = "catalogue"
    preset: str = "white"
    aspect_ratio: str = "1:1"
    marketplace_preset: str | None = None
    photo_id: str | None = None          # default: the product's first photo
    confirm_cost: int = Field(..., ge=0)  # the cost the user saw and agreed to


@router.post("/products/{product_id}/generations", status_code=202)
def generate(product_id: str, body: GenerateIn, tasks: BackgroundTasks,
             idempotency_key: str | None = Header(default=None),
             user: User = Depends(current_user), s=Depends(get_db)):
    """Charges the quoted cost and makes ONE image. Send an Idempotency-Key header so a retried
    request (flaky network) returns the same generation instead of charging twice."""
    product = own_product(s, user, product_id)
    if idempotency_key:
        existing = s.scalar(select(Generation).where(Generation.user_id == user.id,
                                                     Generation.idempotency_key == idempotency_key))
        if existing:
            return JSONResponse(generation_summary(existing), status_code=200)

    if body.output == "catalogue":
        style = STYLES.get(body.preset)
        if not style:
            raise HTTPException(422, f"Unknown preset {body.preset!r}")
        if not style.available:
            raise HTTPException(422, {"code": "preset_unavailable", "message": f"'{style.label}' is coming in a later release."})
        if body.aspect_ratio not in ASPECTS:
            raise HTTPException(422, f"aspect_ratio must be one of {list(ASPECTS)}")
        preset, aspect, mp = body.preset, body.aspect_ratio, None
    elif body.output == "marketplace":
        mp_preset = verified_marketplaces().get(body.marketplace_preset or "")
        if not mp_preset:
            raise HTTPException(422, {"code": "marketplace_unavailable",
                                      "message": "That marketplace preset isn't available yet."})
        preset, aspect, mp = mp_preset.style, f"{mp_preset.width}x{mp_preset.height}", mp_preset.id
    else:
        raise HTTPException(422, "output must be 'catalogue' or 'marketplace'")

    photos = product.photos
    if not photos:
        raise HTTPException(422, {"code": "no_photo", "message": "Add a photo of the piece first."})
    photo = next((p for p in photos if p.id == body.photo_id), None) if body.photo_id else photos[0]
    if not photo:
        raise HTTPException(404, "Photo not found")

    cost, _ = _cost(s, product.id)
    if body.confirm_cost != cost:
        raise HTTPException(409, {"code": "cost_changed", "cost": cost,
                                  "message": f"This image costs {cost} credit(s). Please confirm again."})
    g = Generation(user_id=user.id, product_id=product.id, photo_id=photo.id, output=body.output,
                   preset=preset, aspect=aspect, marketplace_preset=mp, cost=cost,
                   idempotency_key=idempotency_key)
    s.add(g)
    try:
        s.flush()
    except IntegrityError:  # same idempotency key raced in: return the first one
        s.rollback()
        existing = s.scalar(select(Generation).where(Generation.user_id == user.id,
                                                     Generation.idempotency_key == idempotency_key))
        return JSONResponse(generation_summary(existing), status_code=200)
    gid = g.id
    if cost:
        try:
            credits.apply(s, user.id, -cost, "generation", f"generation:{gid}", note=f"Image for {product.name}")
        except credits.InsufficientCredits:
            s.refresh(user)
            raise needs_credits(user, cost - user.credits)
    else:
        s.commit()
    product.updated_at = now()
    s.commit()
    tasks.add_task(process_generation, gid)  # swap for a real queue (RQ/Celery/Arq) when you scale
    return generation_summary(s.get(Generation, gid))


def own_generation(s, user: User, gen_id: str) -> Generation:
    g = s.get(Generation, gen_id)
    if not g or g.user_id != user.id:
        raise HTTPException(404, "Image not found")
    return g


@router.get("/generations/{gen_id}")
def generation_status(gen_id: str, user: User = Depends(current_user), s=Depends(get_db)):
    g = own_generation(s, user, gen_id)
    order = [k for k, _ in STAGES]
    cur = order.index(g.stage) if g.stage in order else -1
    reports = s.scalars(select(Report).where(Report.generation_id == g.id).order_by(Report.created_at))
    return {**generation_summary(g), "stage": g.stage, "message": g.message, "warning": g.warning,
            "width": g.width, "height": g.height, "photo_id": g.photo_id,
            "original_url": f"/generations/{g.id}/original" if g.photo_id else None,
            "original_deleted": g.photo_id is None,
            "steps": [{"id": k, "label": lbl, "done": i < cur or g.status == "done", "active": i == cur and g.status != "done"}
                      for i, (k, lbl) in enumerate(STAGES)],
            "reports": [{"kind": r.kind, "category": r.category, "refund": r.refund} for r in reports],
            "notice": "Please check the details match your piece before using this image to sell it."}


@router.get("/generations/{gen_id}/preview")
def preview(gen_id: str, user: User = Depends(current_user), s=Depends(get_db)):
    """Display-size image for review. Guests see a 'sign in to save' mark until they sign in."""
    g = own_generation(s, user, gen_id)
    if not g.preview_key:
        raise HTTPException(409, {"code": "not_ready", "status": g.status})
    if not user.is_guest:
        return FileResponse(storage.path_for(g.preview_key), media_type="image/jpeg")
    img = watermark(storage.load_image(g.preview_key).convert("RGB"), "Sign in to save")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return Response(buf.getvalue(), media_type="image/jpeg")


@router.get("/generations/{gen_id}/original")
def original(gen_id: str, user: User = Depends(current_user), s=Depends(get_db)):
    """The source photo, for the side-by-side compare."""
    g = own_generation(s, user, gen_id)
    ph = g.photo_id and s.get(SourcePhoto, g.photo_id)
    if not ph:
        raise HTTPException(410, {"code": "original_deleted", "message": "The original photo was deleted."})
    return FileResponse(storage.path_for(ph.original_key))


@router.post("/generations/{gen_id}/accept")
def accept(gen_id: str, user: User = Depends(signed_in_user), s=Depends(get_db)):
    """Save the image to the product's history as accepted."""
    g = own_generation(s, user, gen_id)
    if g.status != "done":
        raise HTTPException(409, {"code": "not_ready", "status": g.status})
    g.review = "accepted"
    s.commit()
    return {"review": g.review}


@router.get("/generations/{gen_id}/download")
def download(gen_id: str, user: User = Depends(signed_in_user), s=Depends(get_db)):
    """Full-size file. Free: the credit was spent when the image was generated."""
    g = own_generation(s, user, gen_id)
    if g.status != "done":
        raise HTTPException(409, {"code": "not_ready", "status": g.status})
    product = s.get(Product, g.product_id)
    ext = g.final_key.rsplit(".", 1)[-1]
    safe = "".join(c if c.isalnum() else "-" for c in product.name).strip("-").lower() or "jewellery"
    headers = {"X-Pixel-Match": f"{g.fidelity:.4f}"}
    if g.warning:
        headers["X-Quality-Warning"] = g.warning
    return FileResponse(storage.path_for(g.final_key), media_type="image/png" if ext == "png" else "image/jpeg",
                        filename=f"{safe}-{g.preset}-{g.width}x{g.height}.{ext}", headers=headers)


class ReportIn(BaseModel):
    kind: str                     # product_detail | visual_quality
    category: str
    note: str = Field("", max_length=1000)


@router.post("/generations/{gen_id}/report", status_code=201)
def report(gen_id: str, body: ReportIn, user: User = Depends(current_user), s=Depends(get_db)):
    """Report a problem (§9.5). A changed jewellery detail returns the credit automatically
    (§12.3), once per image, up to QUALITY_REFUND_AUTO_LIMIT per 30 days; beyond that the report
    goes to manual review. Visual-quality reports are recorded but not refunded."""
    g = own_generation(s, user, gen_id)
    if g.status != "done":
        raise HTTPException(409, {"code": "not_ready", "status": g.status})
    issues = DETAIL_ISSUES if body.kind == "product_detail" else QUALITY_ISSUES if body.kind == "visual_quality" else None
    if issues is None or body.category not in issues:
        raise HTTPException(422, "Unknown report kind or category")

    refund = "not_eligible"
    if body.kind == "product_detail" and g.cost:
        ref = f"refund:quality:{g.id}"
        already = s.scalar(select(CreditEntry.id).where(CreditEntry.ref == ref))
        recent = s.scalar(select(func.count(CreditEntry.id)).where(
            CreditEntry.user_id == user.id, CreditEntry.reason == "refund_quality",
            CreditEntry.created_at >= now() - timedelta(days=30)))
        if already:
            refund = "duplicate"
        elif recent >= get_settings().quality_refund_auto_limit:
            refund = "under_review"
        else:
            credits.apply(s, user.id, +g.cost, "refund_quality", ref, note="Reported a changed jewellery detail")
            refund = "refunded"
    product = s.get(Product, g.product_id)
    s.add(Report(generation_id=g.id, user_id=user.id, kind=body.kind, category=body.category,
                 note=body.note, refund=refund, product_category=product.category, preset=g.preset))
    g = s.get(Generation, gen_id)
    g.review = "reported"
    s.commit()
    messages = {
        "refunded": "Thanks for telling us. Your credit has been returned, so you can try again.",
        "duplicate": "Thanks. This image has already been refunded.",
        "under_review": "Thanks. We'll review this report and return your credit if the detail changed.",
        "not_eligible": "Thanks for the feedback. It helps us improve image quality.",
    }
    s.refresh(user)
    return {"refund": refund, "message": messages[refund], "balance": user.credits}


@router.delete("/generations/{gen_id}", status_code=204)
def delete_generation(gen_id: str, user: User = Depends(current_user), s=Depends(get_db)):
    """Deletes the image and its files. Report records stay (without the image) for quality analysis."""
    g = own_generation(s, user, gen_id)
    if g.status in ("queued", "running"):
        raise HTTPException(409, {"code": "in_progress", "message": "Wait for the image to finish, then delete it."})
    delete_generation_files(g)
    s.delete(g)
    s.commit()
