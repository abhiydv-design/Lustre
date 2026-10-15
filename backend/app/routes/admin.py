"""Operations console for the team (served at /admin).

Access rules (spec §14: support access to user images must be limited and governed):
- Only people listed in ADMIN_TOKENS can use it; without any tokens configured, /admin doesn't exist.
- Staff can see a customer image only through a quality report, and every view is written to
  the audit log with the staff member's name.
- Customer phone numbers are never shown; customers appear by a short id.
"""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from .. import credits, metrics, storage
from ..admin_page import PAGE
from ..config import get_settings
from ..db import AdminAudit, CreditEntry, Generation, Product, Report, SourcePhoto, User, now
from ..deps import get_db
from .generations import DETAIL_ISSUES, QUALITY_ISSUES

router = APIRouter()


def _enabled():
    if not get_settings().admin_tokens:
        raise HTTPException(404)


def admin(authorization: str | None = Header(default=None), _=Depends(_enabled)) -> str:
    token = (authorization or "").removeprefix("Bearer ").strip()
    name = get_settings().admin_tokens.get(token)
    if not name:
        raise HTTPException(401, "Admin token required")
    return name


def audit(s, who: str, action: str, target: str = "", detail: str = "") -> None:
    s.add(AdminAudit(admin=who, action=action, target=target, detail=detail[:500]))
    s.commit()


@router.get("/admin", response_class=HTMLResponse, dependencies=[Depends(_enabled)])
def page():
    return PAGE


@router.get("/admin/api/metrics")
def get_metrics(days: int = 30, who: str = Depends(admin), s=Depends(get_db)):
    days = max(1, min(days, 365))
    audit(s, who, "view_metrics", detail=f"{days} days")
    return metrics.compute(s, days)


def _signals(s, user_id: str) -> dict:
    """Context for judging a refund claim, without identifying the customer."""
    since = now() - timedelta(days=30)
    u = s.get(User, user_id)
    created = u.created_at if u.created_at.tzinfo else u.created_at.replace(tzinfo=now().tzinfo)
    count = lambda q: s.scalar(q) or 0
    return {
        "customer": user_id[:8],
        "signed_in": not u.is_guest,
        "account_age_days": (now() - created).days,
        "images_made": count(select(func.count(Generation.id)).where(Generation.user_id == user_id, Generation.status == "done")),
        "images_accepted": count(select(func.count(Generation.id)).where(Generation.user_id == user_id, Generation.review == "accepted")),
        "detail_reports_30d": count(select(func.count(Report.id)).where(
            Report.user_id == user_id, Report.kind == "product_detail", Report.created_at >= since)),
        "quality_refunds_30d": count(select(func.count(CreditEntry.id)).where(
            CreditEntry.user_id == user_id, CreditEntry.reason == "refund_quality", CreditEntry.created_at >= since)),
        "credits_bought": count(select(func.coalesce(func.sum(CreditEntry.delta), 0)).where(
            CreditEntry.user_id == user_id, CreditEntry.reason == "purchase")),
    }


def _report_view(s, r: Report) -> dict:
    g = s.get(Generation, r.generation_id)
    labels = DETAIL_ISSUES if r.kind == "product_detail" else QUALITY_ISSUES
    return {
        "id": r.id, "kind": r.kind, "category": r.category, "category_label": labels.get(r.category, r.category),
        "note": r.note, "status": r.refund, "created_at": r.created_at.isoformat(),
        "product_category": r.product_category, "preset": r.preset,
        "image_available": bool(g and g.status == "done" and g.final_key),
        "original_available": bool(g and g.photo_id and s.get(SourcePhoto, g.photo_id)),
        "pixel_match": g.fidelity if g else None,
        "resolved_by": r.resolved_by, "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
        "user_message": r.user_message, "internal_note": r.internal_note,
        "signals": _signals(s, r.user_id),
    }


@router.get("/admin/api/reports")
def list_reports(status: str = "under_review", limit: int = 50, who: str = Depends(admin), s=Depends(get_db)):
    q = select(Report).order_by(Report.created_at)
    if status != "all":
        q = q.where(Report.refund == status)
    rows = list(s.scalars(q.limit(max(1, min(limit, 200)))))
    audit(s, who, "view_queue", detail=f"status={status}, {len(rows)} rows")
    return [_report_view(s, r) for r in rows]


@router.get("/admin/api/reports/{report_id}/image/{which}")
def report_image(report_id: str, which: str, who: str = Depends(admin), s=Depends(get_db)):
    """The only way staff can see a customer image. Every call is audit-logged."""
    r = s.get(Report, report_id)
    if not r or which not in ("output", "original"):
        raise HTTPException(404)
    g = s.get(Generation, r.generation_id)
    if which == "output":
        key = g and g.status == "done" and g.preview_key
    else:
        ph = g and g.photo_id and s.get(SourcePhoto, g.photo_id)
        key = ph and ph.original_key
    if not key:
        raise HTTPException(410, "The customer deleted this image.")
    audit(s, who, "view_image", target=report_id, detail=which)
    return FileResponse(storage.path_for(key), headers={"Cache-Control": "no-store"})


class Resolution(BaseModel):
    decision: str                                   # approve | decline
    user_message: str = Field("", max_length=500)   # shown to the jeweller
    internal_note: str = Field("", max_length=1000)


@router.post("/admin/api/reports/{report_id}/resolve")
def resolve(report_id: str, body: Resolution, who: str = Depends(admin), s=Depends(get_db)):
    r = s.get(Report, report_id)
    if not r:
        raise HTTPException(404)
    if r.refund != "under_review":
        raise HTTPException(409, f"This report is already '{r.refund}'.")
    if body.decision not in ("approve", "decline"):
        raise HTTPException(422, "decision must be approve or decline")
    if body.decision == "decline" and not body.user_message.strip():
        raise HTTPException(422, "Tell the customer why when declining.")

    if body.decision == "approve":
        # The original charge is in the ledger even if the image was since deleted.
        charge = s.scalar(select(CreditEntry).where(CreditEntry.ref == f"generation:{r.generation_id}"))
        amount = -charge.delta if charge else 0
        applied = amount > 0 and credits.apply(
            s, r.user_id, amount, "refund_quality", f"refund:quality:{r.generation_id}",
            note="Refund after review of a reported detail")
        r = s.get(Report, report_id)
        r.refund = "refunded" if applied else "duplicate"
        r.user_message = body.user_message.strip() or "We checked your report and returned your credit."
    else:
        r.refund = "declined"
        r.user_message = body.user_message.strip()
    r.resolved_by, r.resolved_at, r.internal_note = who, now(), body.internal_note.strip() or None
    s.commit()
    audit(s, who, "resolve_report", target=report_id, detail=f"{body.decision} -> {r.refund}")
    return _report_view(s, r)


@router.get("/admin/api/audit")
def audit_log(limit: int = 100, who: str = Depends(admin), s=Depends(get_db)):
    rows = s.scalars(select(AdminAudit).order_by(AdminAudit.id.desc()).limit(max(1, min(limit, 500))))
    return [{"admin": a.admin, "action": a.action, "target": a.target, "detail": a.detail,
             "at": a.created_at.isoformat()} for a in rows]
