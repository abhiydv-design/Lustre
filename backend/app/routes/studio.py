"""Upload → choose a look → generate → results → 4K download. One endpoint group per prototype screen."""
from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from .. import credits, storage
from ..config import get_settings
from ..db import Job, Shoot, SourcePhoto, User, Variation
from ..deps import current_user, get_db
from ..pipeline.geometry import FORMATS
from ..pipeline.prepare import load_photo
from ..pipeline.run import process_final, process_job
from ..pipeline.styles import STYLES

router = APIRouter()

JEWELLERY_TYPES = ["ring", "necklace", "earrings", "bangle", "pendant"]
METALS = ["yellow_gold", "rose_gold", "white_gold", "silver", "platinum"]
STAGES = [
    ("cutout", "Cutting out your piece"),
    ("scene", "Building the scene"),
    ("lighting", "Matching light and shadow"),
    ("ready", "Previews ready"),
]


@router.get("/catalog")
def catalog():
    """Options for the Upload and Choose-a-look screens."""
    return {
        "jewellery_types": JEWELLERY_TYPES,
        "metals": METALS,
        "styles": [{"id": s.id, "label": s.label, "available": s.available} for s in STYLES.values()],
        "formats": [{"id": k, "width": w, "height": h} for k, (w, h) in FORMATS.items()],
        "variation_counts": [2, 4, 6],
    }


# ---------- Screen 2: upload ----------

@router.post("/shoots", status_code=201)
async def create_shoot(
    jewellery_type: str = Form(...),
    metal: str = Form(...),
    files: list[UploadFile] = File(...),
    user: User = Depends(current_user),
    s=Depends(get_db),
):
    settings = get_settings()
    if jewellery_type not in JEWELLERY_TYPES:
        raise HTTPException(422, f"jewellery_type must be one of {JEWELLERY_TYPES}")
    if metal not in METALS:
        raise HTTPException(422, f"metal must be one of {METALS}")
    if not 1 <= len(files) <= 4:
        raise HTTPException(422, "Upload between 1 and 4 photos of the same piece")

    shoot = Shoot(user_id=user.id, jewellery_type=jewellery_type, metal=metal)
    s.add(shoot)
    s.flush()
    for i, f in enumerate(files):
        data = await f.read()
        if len(data) > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(413, f"{f.filename} is larger than {settings.max_upload_mb} MB")
        try:
            Image.open(io.BytesIO(data)).verify()
            image = load_photo(data)
        except Exception:
            raise HTTPException(422, f"{f.filename} is not a readable image (JPG, PNG or HEIC)")
        if min(image.size) < 800:
            raise HTTPException(422, f"{f.filename} is too small ({image.width}×{image.height}); use at least 800 px")
        photo = SourcePhoto(shoot_id=shoot.id, position=i, original_key="", width=image.width, height=image.height)
        s.add(photo)
        s.flush()
        ext = (f.filename or "photo.jpg").rsplit(".", 1)[-1].lower()[:5] or "jpg"
        photo.original_key = storage.save_bytes(f"shoots/{shoot.id}/{photo.id}_original.{ext}", data)
    s.commit()
    return {"id": shoot.id, "photos": len(files)}


# ---------- Screens 3-4: choose a look, generate ----------

class JobRequest(BaseModel):
    style: str
    format: str = "1:1"
    count: int = Field(4, ge=1, le=6)


@router.post("/shoots/{shoot_id}/jobs", status_code=202)
def start_job(shoot_id: str, body: JobRequest, tasks: BackgroundTasks,
              user: User = Depends(current_user), s=Depends(get_db)):
    shoot = s.get(Shoot, shoot_id)
    if not shoot or shoot.user_id != user.id:
        raise HTTPException(404, "Shoot not found")
    style = STYLES.get(body.style)
    if not style:
        raise HTTPException(422, f"Unknown style {body.style!r}")
    if not style.available:
        raise HTTPException(422, f"'{style.label}' is coming soon")
    if body.format not in FORMATS:
        raise HTTPException(422, f"format must be one of {list(FORMATS)}")
    since = datetime.now(timezone.utc) - timedelta(days=1)
    recent = s.scalar(select(func.count(Job.id)).where(Job.user_id == user.id, Job.created_at >= since))
    if recent >= get_settings().daily_preview_jobs:
        raise HTTPException(429, "Daily preview limit reached. Try again tomorrow.")

    job = Job(shoot_id=shoot.id, user_id=user.id, style=style.id, fmt=body.format, count=body.count)
    s.add(job)
    s.commit()
    tasks.add_task(process_job, job.id)  # swap for a real queue (RQ/Celery/Arq) when you scale
    return {"id": job.id, "status": job.status}


@router.get("/jobs/{job_id}")
def job_status(job_id: str, user: User = Depends(current_user), s=Depends(get_db)):
    job = s.get(Job, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(404, "Job not found")
    order = [k for k, _ in STAGES]
    current = order.index(job.stage) if job.stage in order else -1
    return {
        "id": job.id, "status": job.status, "stage": job.stage, "error": job.error,
        "style": job.style, "format": job.fmt, "count": job.count,
        "steps": [{"id": k, "label": label, "done": i < current or job.status == "done", "active": i == current}
                  for i, (k, label) in enumerate(STAGES)],
        "variations": [{
            "id": v.id, "preview_url": f"/variations/{v.id}/preview",
            "fidelity": round(v.preview_fidelity, 4), "final_status": v.final_status,
        } for v in job.variations],
    }


# ---------- Screen 5: results and 4K download ----------

def _own_variation(s, user: User, variation_id: str) -> tuple[Variation, Job]:
    v = s.get(Variation, variation_id)
    job = v and s.get(Job, v.job_id)
    if not v or job.user_id != user.id:
        raise HTTPException(404, "Photo not found")
    return v, job


@router.get("/variations/{variation_id}/preview")
def preview(variation_id: str, user: User = Depends(current_user), s=Depends(get_db)):
    v, _ = _own_variation(s, user, variation_id)
    return FileResponse(storage.path_for(v.preview_key), media_type="image/jpeg")


@router.get("/variations/{variation_id}/original")
def original(variation_id: str, user: User = Depends(current_user), s=Depends(get_db)):
    """For the 'Compare with original' toggle."""
    v, _ = _own_variation(s, user, variation_id)
    return FileResponse(storage.path_for(s.get(SourcePhoto, v.photo_id).original_key))


@router.post("/variations/{variation_id}/download", status_code=202)
def request_download(variation_id: str, tasks: BackgroundTasks,
                     user: User = Depends(current_user), s=Depends(get_db)):
    """Charges 1 credit (once) and renders the 4K file. Re-downloading is free."""
    v, _ = _own_variation(s, user, variation_id)
    if v.final_status in ("rendering", "ready"):
        return {"status": v.final_status}
    ref = f"download:{v.id}:{v.render_attempts}"
    try:
        credits.apply(s, user.id, -1, "download", ref)
    except credits.InsufficientCredits:
        raise HTTPException(402, "Not enough credits")
    v = s.get(Variation, variation_id)
    v.final_status, v.render_attempts = "rendering", v.render_attempts + 1
    s.commit()
    tasks.add_task(process_final, v.id, ref)
    return {"status": "rendering"}


@router.get("/variations/{variation_id}/download")
def download(variation_id: str, user: User = Depends(current_user), s=Depends(get_db)):
    v, job = _own_variation(s, user, variation_id)
    if v.final_status != "ready":
        return JSONResponse({"status": v.final_status}, status_code=202 if v.final_status == "rendering" else 409)
    w, h = FORMATS[job.fmt]
    headers = {"X-Fidelity": f"{v.final_fidelity:.4f}"}
    if v.warning:
        headers["X-Quality-Warning"] = v.warning
    return FileResponse(storage.path_for(v.final_key), media_type="image/png",
                        filename=f"{job.style}-{w}x{h}-{v.id[:6]}.png", headers=headers)
