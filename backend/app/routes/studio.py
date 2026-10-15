"""Upload → (auto) generate → results → 4K download. Built so the jeweller never fills a form or waits twice."""
from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from PIL import Image
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from .. import credits, storage
from ..config import get_settings
from ..db import Job, Shoot, SourcePhoto, User, Variation
from ..deps import current_user, get_db
from ..downloads import owned_variations, pay_and_queue
from ..pipeline.geometry import FORMATS
from ..pipeline.inspect import photo_hints
from ..pipeline.prepare import load_photo
from ..pipeline.run import process_final, process_job
from ..pipeline.styles import STYLES

router = APIRouter()

JEWELLERY_TYPES = ["auto", "ring", "necklace", "earrings", "bangle", "pendant"]
METALS = ["auto", "yellow_gold", "rose_gold", "white_metal", "white_gold", "silver", "platinum"]
STAGES = [
    ("cutout", "Cutting out your piece"),
    ("scene", "Building the scene"),
    ("lighting", "Matching light and shadow"),
    ("ready", "Previews ready"),
]
MAX_PHOTOS = 4


def needs_credits(exc: credits.InsufficientCredits) -> HTTPException:
    """402 that carries everything the app needs to open checkout right away."""
    from .payments import packs
    return HTTPException(402, {"code": "needs_credits", "needed": exc.needed, "balance": exc.balance,
                               "packs": packs()})


@router.get("/catalog")
def catalog():
    return {
        "jewellery_types": JEWELLERY_TYPES,
        "metals": METALS,
        "styles": [{"id": s.id, "label": s.label, "available": s.available} for s in STYLES.values()],
        "formats": [{"id": k, "width": w, "height": h} for k, (w, h) in FORMATS.items()],
        "variation_counts": [2, 4, 6],
    }


def _start_job(s, tasks: BackgroundTasks, user: User, shoot: Shoot, style_id: str, fmt: str, count: int) -> Job:
    style = STYLES.get(style_id)
    if not style:
        raise HTTPException(422, f"Unknown style {style_id!r}")
    if not style.available:
        raise HTTPException(422, f"'{style.label}' is coming soon")
    if fmt not in FORMATS:
        raise HTTPException(422, f"format must be one of {list(FORMATS)}")
    since = datetime.now(timezone.utc) - timedelta(days=1)
    recent = s.scalar(select(func.count(Job.id)).where(Job.user_id == user.id, Job.created_at >= since))
    if recent >= get_settings().daily_preview_jobs:
        raise HTTPException(429, "You've made a lot of previews today. More will be free again tomorrow.")
    job = Job(shoot_id=shoot.id, user_id=user.id, style=style.id, fmt=fmt, count=count)
    s.add(job)
    s.commit()
    tasks.add_task(process_job, job.id)  # swap for a real queue (RQ/Celery/Arq) when you scale
    return job


# ---------- Upload: photos only. Everything else is optional or detected. ----------

@router.post("/shoots", status_code=201)
async def create_shoot(
    tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    jewellery_type: str = Form("auto"),
    metal: str = Form("auto"),
    auto_generate: bool = Form(True),
    format: str = Form("1:1"),
    user: User = Depends(current_user),
    s=Depends(get_db),
):
    settings = get_settings()
    if jewellery_type not in JEWELLERY_TYPES:
        jewellery_type = "auto"
    if metal not in METALS:
        metal = "auto"
    if format not in FORMATS:
        format = "1:1"
    notices = []
    if len(files) > MAX_PHOTOS:
        notices.append(f"We used the first {MAX_PHOTOS} photos. One piece per shoot works best.")
        files = files[:MAX_PHOTOS]

    shoot = Shoot(user_id=user.id, jewellery_type=jewellery_type, metal=metal)
    s.add(shoot)
    s.flush()
    photos = []
    for f in files:
        data = await f.read()
        if len(data) > settings.max_upload_mb * 1024 * 1024:
            notices.append(f"{f.filename} was over {settings.max_upload_mb} MB, so we skipped it.")
            continue
        try:
            Image.open(io.BytesIO(data)).verify()
            image = load_photo(data)
        except Exception:
            notices.append(f"We couldn't open {f.filename}. JPG, PNG and iPhone HEIC photos all work.")
            continue
        if min(image.size) < 300:
            notices.append(f"{f.filename} is too small to use ({image.width}×{image.height}).")
            continue
        photo = SourcePhoto(shoot_id=shoot.id, position=len(photos), original_key="",
                            width=image.width, height=image.height, hints=json.dumps(photo_hints(image)))
        s.add(photo)
        s.flush()
        ext = (f.filename or "photo.jpg").rsplit(".", 1)[-1].lower()[:5] or "jpg"
        photo.original_key = storage.save_bytes(f"shoots/{shoot.id}/{photo.id}_original.{ext}", data)
        photos.append(photo)
    if not photos:
        s.rollback()
        raise HTTPException(422, {"code": "no_usable_photos", "notices": notices})
    s.commit()

    jobs = []
    if auto_generate:
        for style_id, count in settings.auto_jobs:
            try:
                jobs.append(_start_job(s, tasks, user, shoot, style_id, format, count))
            except HTTPException as e:
                if e.status_code == 429:
                    notices.append(e.detail)
                    break
                raise
    return {"id": shoot.id, "notices": notices,
            "photos": [{"id": p.id, "hints": json.loads(p.hints)} for p in photos],
            "jobs": [{"id": j.id, "style": j.style, "count": j.count} for j in jobs]}


def _own_shoot(s, user: User, shoot_id: str) -> Shoot:
    shoot = s.get(Shoot, shoot_id)
    if not shoot or shoot.user_id != user.id:
        raise HTTPException(404, "Shoot not found")
    return shoot


@router.get("/shoots/{shoot_id}")
def shoot_detail(shoot_id: str, user: User = Depends(current_user), s=Depends(get_db)):
    shoot = _own_shoot(s, user, shoot_id)
    jobs = s.scalars(select(Job).where(Job.shoot_id == shoot.id).order_by(Job.created_at))
    return {
        "id": shoot.id, "jewellery_type": shoot.jewellery_type,
        "metal": shoot.metal, "metal_detected": shoot.metal_detected,
        "photos": [{"id": p.id, "hints": json.loads(p.hints)} for p in shoot.photos],
        "jobs": [{"id": j.id, "style": j.style, "status": j.status, "count": j.count} for j in jobs],
    }


class ShootUpdate(BaseModel):
    jewellery_type: str | None = None
    metal: str | None = None


@router.patch("/shoots/{shoot_id}")
def correct_shoot(shoot_id: str, body: ShootUpdate, user: User = Depends(current_user), s=Depends(get_db)):
    """One-tap correction if the detected metal is wrong."""
    shoot = _own_shoot(s, user, shoot_id)
    if body.metal:
        if body.metal not in METALS:
            raise HTTPException(422, f"metal must be one of {METALS}")
        shoot.metal, shoot.metal_detected = body.metal, False
    if body.jewellery_type:
        if body.jewellery_type not in JEWELLERY_TYPES:
            raise HTTPException(422, f"jewellery_type must be one of {JEWELLERY_TYPES}")
        shoot.jewellery_type = body.jewellery_type
    s.commit()
    return {"ok": True}


# ---------- Another look (optional) ----------

class JobRequest(BaseModel):
    style: str
    format: str = "1:1"
    count: int = Field(4, ge=1, le=6)


@router.post("/shoots/{shoot_id}/jobs", status_code=202)
def start_job(shoot_id: str, body: JobRequest, tasks: BackgroundTasks,
              user: User = Depends(current_user), s=Depends(get_db)):
    job = _start_job(s, tasks, user, _own_shoot(s, user, shoot_id), body.style, body.format, body.count)
    return {"id": job.id, "status": job.status}


@router.get("/jobs/{job_id}")
def job_status(job_id: str, user: User = Depends(current_user), s=Depends(get_db)):
    job = s.get(Job, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(404, "Job not found")
    order = [k for k, _ in STAGES]
    current = order.index(job.stage) if job.stage in order else -1
    return {
        "id": job.id, "status": job.status, "stage": job.stage, "message": job.error,
        "style": job.style, "format": job.fmt, "count": job.count,
        "steps": [{"id": k, "label": label, "done": i < current or job.status == "done", "active": i == current}
                  for i, (k, label) in enumerate(STAGES)],
        "variations": [{
            "id": v.id, "preview_url": f"/variations/{v.id}/preview",
            "fidelity": round(v.preview_fidelity, 4), "paid": v.paid,
            "instant": v.final_status == "ready",  # 4K already rendered: download is immediate
        } for v in job.variations],
    }


# ---------- Results and downloads ----------

def _one(s, user: User, variation_id: str) -> Variation:
    try:
        return owned_variations(s, user.id, [variation_id])[0]
    except LookupError:
        raise HTTPException(404, "Photo not found")


@router.get("/variations/{variation_id}/preview")
def preview(variation_id: str, user: User = Depends(current_user), s=Depends(get_db)):
    return FileResponse(storage.path_for(_one(s, user, variation_id).preview_key), media_type="image/jpeg")


@router.get("/variations/{variation_id}/original")
def original(variation_id: str, user: User = Depends(current_user), s=Depends(get_db)):
    v = _one(s, user, variation_id)
    return FileResponse(storage.path_for(s.get(SourcePhoto, v.photo_id).original_key))


@router.post("/variations/{variation_id}/prepare", status_code=202)
def prepare(variation_id: str, tasks: BackgroundTasks, user: User = Depends(current_user), s=Depends(get_db)):
    """Free: the app calls this when the jeweller opens a photo full-screen, so 'Download' is instant."""
    v = _one(s, user, variation_id)
    if v.final_status in ("rendering", "ready"):
        return {"status": v.final_status}
    warmed = s.scalar(select(func.count(Variation.id)).where(
        Variation.job_id == v.job_id, Variation.paid.is_(False), Variation.final_status != "none"))
    if warmed >= get_settings().prerender_per_job + 2:
        return {"status": "none"}  # cost cap; download still works, it just renders then
    v.final_status = "rendering"
    s.commit()
    tasks.add_task(process_final, v.id)
    return {"status": "rendering"}


@router.post("/variations/{variation_id}/download", status_code=202)
def request_download(variation_id: str, tasks: BackgroundTasks,
                     user: User = Depends(current_user), s=Depends(get_db)):
    """Charges 1 credit once. Re-downloads are free. Usually the 4K file is already waiting."""
    _one(s, user, variation_id)
    try:
        for vid in pay_and_queue(s, user.id, [variation_id]):
            tasks.add_task(process_final, vid)
    except credits.InsufficientCredits as exc:
        raise needs_credits(exc)
    return {"status": s.get(Variation, variation_id).final_status}


@router.get("/variations/{variation_id}/download")
def download(variation_id: str, user: User = Depends(current_user), s=Depends(get_db)):
    v = _one(s, user, variation_id)
    if not v.paid:
        return JSONResponse({"status": "unpaid"}, status_code=409)
    if v.final_status != "ready":
        return JSONResponse({"status": v.final_status}, status_code=202 if v.final_status == "rendering" else 409)
    job = s.get(Job, v.job_id)
    w, h = FORMATS[job.fmt]
    headers = {"X-Fidelity": f"{v.final_fidelity:.4f}"}
    if v.warning:
        headers["X-Quality-Warning"] = v.warning
    return FileResponse(storage.path_for(v.final_key), media_type="image/png",
                        filename=f"{job.style}-{w}x{h}-{v.id[:6]}.png", headers=headers)


class BulkRequest(BaseModel):
    variation_ids: list[str] | None = None  # default: every photo in the job


@router.post("/jobs/{job_id}/download-all", status_code=202)
def request_download_all(job_id: str, tasks: BackgroundTasks, body: BulkRequest | None = None,
                         user: User = Depends(current_user), s=Depends(get_db)):
    job = s.get(Job, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(404, "Job not found")
    ids = (body and body.variation_ids) or [v.id for v in job.variations]
    if any(s.get(Variation, i) is None or s.get(Variation, i).job_id != job.id for i in ids):
        raise HTTPException(404, "Photo not found")
    try:
        for vid in pay_and_queue(s, user.id, ids):
            tasks.add_task(process_final, vid)
    except credits.InsufficientCredits as exc:
        raise needs_credits(exc)
    return {"status": "rendering", "count": len(ids)}


@router.get("/jobs/{job_id}/download-all")
def download_all(job_id: str, user: User = Depends(current_user), s=Depends(get_db)):
    """A zip of every paid photo in the job, once they're all rendered."""
    job = s.get(Job, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(404, "Job not found")
    paid = [v for v in job.variations if v.paid]
    ready = [v for v in paid if v.final_status == "ready"]
    if not paid:
        return JSONResponse({"status": "unpaid"}, status_code=409)
    if len(ready) < len(paid):
        return JSONResponse({"status": "rendering", "ready": len(ready), "total": len(paid)}, status_code=202)
    w, h = FORMATS[job.fmt]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:  # PNGs are already compressed
        for i, v in enumerate(ready, 1):
            z.write(storage.path_for(v.final_key), f"{job.style}-{w}x{h}-{i}.png")
    return Response(buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{job.style}-photos.zip"'})
