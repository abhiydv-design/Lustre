"""Product catalogue (spec §9.3) and source photos (§9.2)."""
from __future__ import annotations

import io
import json

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from PIL import Image
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from .. import storage
from ..config import get_settings
from ..db import Generation, Product, SourcePhoto, User
from ..deps import current_user, get_db
from ..pipeline.inspect import photo_hints
from ..pipeline.prepare import load_photo
from ..pipeline.run import ensure_prepared

router = APIRouter()

CATEGORIES = {
    "ring": ("Ring", "अंगूठी"), "earrings": ("Earrings", "झुमके / बालियाँ"), "necklace": ("Necklace", "हार"),
    "pendant": ("Pendant", "पेंडेंट"), "bracelet": ("Bracelet", "ब्रेसलेट"), "bangle": ("Bangle", "चूड़ी / कंगन"),
    "chain": ("Chain", "चेन"), "anklet": ("Anklet", "पायल"), "set": ("Jewellery set", "ज्वेलरी सेट"),
    "other": ("Other", "अन्य"),
}
METALS = ["yellow_gold", "rose_gold", "white_gold", "silver", "platinum", "white_metal", "other"]


def own_product(s, user: User, product_id: str) -> Product:
    product = s.get(Product, product_id)
    if not product or product.user_id != user.id:
        raise HTTPException(404, "Product not found")
    return product


def generation_summary(g: Generation) -> dict:
    return {"id": g.id, "product_id": g.product_id, "status": g.status, "review": g.review, "output": g.output, "preset": g.preset,
            "aspect": g.aspect, "marketplace_preset": g.marketplace_preset, "cost": g.cost,
            "preview_url": f"/generations/{g.id}/preview" if g.preview_key else None,
            "created_at": g.created_at.isoformat()}


def product_summary(s, p: Product) -> dict:
    cover = s.scalar(select(Generation).where(Generation.product_id == p.id, Generation.status == "done")
                     .order_by(Generation.created_at.desc()))
    return {"id": p.id, "name": p.name, "category": p.category, "sku": p.sku,
            "metal": p.metal, "metal_source": p.metal_source, "stone": p.stone,
            "collection": p.collection, "notes": p.notes,
            "photo_count": len(p.photos),
            "image_count": s.scalar(select(func.count(Generation.id)).where(
                Generation.product_id == p.id, Generation.status == "done")),
            "cover_url": f"/generations/{cover.id}/preview" if cover else None,
            "updated_at": p.updated_at.isoformat()}


class ProductIn(BaseModel):
    category: str
    name: str | None = Field(None, max_length=120)
    sku: str | None = Field(None, max_length=60)
    metal: str | None = None
    stone: str | None = Field(None, max_length=60)
    collection: str | None = Field(None, max_length=80)
    notes: str | None = Field(None, max_length=2000)


@router.post("/products", status_code=201)
def create_product(body: ProductIn, user: User = Depends(current_user), s=Depends(get_db)):
    if body.category not in CATEGORIES:
        raise HTTPException(422, f"category must be one of {list(CATEGORIES)}")
    if body.metal and body.metal not in METALS:
        raise HTTPException(422, f"metal must be one of {METALS}")
    name = (body.name or "").strip()
    if not name:  # name is required (§9.3) but we suggest one so the user never has to type
        n = s.scalar(select(func.count(Product.id)).where(Product.user_id == user.id,
                                                         Product.category == body.category)) + 1
        name = f"{CATEGORIES[body.category][0]} {n}"
    p = Product(user_id=user.id, name=name, category=body.category, sku=body.sku, metal=body.metal,
                metal_source="user" if body.metal else None, stone=body.stone,
                collection=body.collection, notes=body.notes)
    s.add(p)
    s.commit()
    return product_summary(s, p)


@router.get("/products")
def list_products(user: User = Depends(current_user), s=Depends(get_db)):
    rows = s.scalars(select(Product).where(Product.user_id == user.id).order_by(Product.updated_at.desc()))
    return [product_summary(s, p) for p in rows]


@router.get("/products/{product_id}")
def product_detail(product_id: str, user: User = Depends(current_user), s=Depends(get_db)):
    """The product's photos and full image history."""
    p = own_product(s, user, product_id)
    gens = s.scalars(select(Generation).where(Generation.product_id == p.id).order_by(Generation.created_at.desc()))
    return {**product_summary(s, p),
            "photos": [{"id": ph.id, "url": f"/photos/{ph.id}", "hints": json.loads(ph.hints)} for ph in p.photos],
            "images": [generation_summary(g) for g in gens]}


class ProductPatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    category: str | None = None
    sku: str | None = Field(None, max_length=60)
    metal: str | None = None
    stone: str | None = Field(None, max_length=60)
    collection: str | None = Field(None, max_length=80)
    notes: str | None = Field(None, max_length=2000)


@router.patch("/products/{product_id}")
def update_product(product_id: str, body: ProductPatch, user: User = Depends(current_user), s=Depends(get_db)):
    """Rename, recategorise, or correct the detected metal."""
    p = own_product(s, user, product_id)
    data = body.model_dump(exclude_unset=True)
    if "category" in data and data["category"] not in CATEGORIES:
        raise HTTPException(422, f"category must be one of {list(CATEGORIES)}")
    if data.get("metal") and data["metal"] not in METALS:
        raise HTTPException(422, f"metal must be one of {METALS}")
    for k, v in data.items():
        setattr(p, k, v.strip() if isinstance(v, str) else v)
    if "metal" in data:
        p.metal_source = "user" if data["metal"] else None
    s.commit()
    return product_summary(s, p)


def delete_generation_files(g: Generation) -> None:
    for key in (g.scene_key, g.preview_key, g.final_key):
        storage.delete(key)


def delete_product_everything(s, product_id: str) -> None:
    p = s.get(Product, product_id)
    for g in s.scalars(select(Generation).where(Generation.product_id == product_id)):
        delete_generation_files(g)
        s.delete(g)
    for ph in list(p.photos):
        s.delete(ph)
    storage.delete_prefix(f"products/{product_id}")
    s.delete(p)
    s.commit()


@router.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: str, user: User = Depends(current_user), s=Depends(get_db)):
    """Deletes the product, its source photos and every generated image, including the files."""
    own_product(s, user, product_id)
    delete_product_everything(s, product_id)


# ---------- Source photos ----------

@router.post("/products/{product_id}/photos", status_code=201)
async def add_photos(product_id: str, tasks: BackgroundTasks, files: list[UploadFile] = File(...),
                     user: User = Depends(current_user), s=Depends(get_db)):
    """One photo is enough; extra angles are optional (§9.2). Problems become tips, not rejections."""
    settings = get_settings()
    p = own_product(s, user, product_id)
    room = settings.max_photos_per_product - len(p.photos)
    notices, added = [], []
    if room <= 0:
        raise HTTPException(422, {"code": "too_many_photos",
                                  "message": f"A product can have up to {settings.max_photos_per_product} photos. Delete one to add another."})
    if len(files) > room:
        notices.append(f"We added the first {room} photos; a product can have up to {settings.max_photos_per_product}.")
        files = files[:room]
    for f in files:
        data = await f.read()
        if len(data) > settings.max_upload_mb * 1024 * 1024:
            notices.append(f"{f.filename} is over {settings.max_upload_mb} MB, so we skipped it.")
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
        ph = SourcePhoto(product_id=p.id, position=len(p.photos) + len(added), original_key="",
                         width=image.width, height=image.height, hints=json.dumps(photo_hints(image)))
        s.add(ph)
        s.flush()
        ext = (f.filename or "photo.jpg").rsplit(".", 1)[-1].lower()[:5] or "jpg"
        ph.original_key = storage.save_bytes(f"products/{p.id}/{ph.id}_original.{ext}", data)
        added.append(ph)
    if not added:
        s.rollback()
        raise HTTPException(422, {"code": "no_usable_photos", "notices": notices})
    s.commit()
    for ph in added:  # cut out + detect metal now, so the first generation starts faster
        tasks.add_task(_prepare_quietly, ph.id)
    return {"photos": [{"id": ph.id, "url": f"/photos/{ph.id}", "hints": json.loads(ph.hints)} for ph in added],
            "notices": notices}


def _prepare_quietly(photo_id: str) -> None:
    try:
        ensure_prepared(photo_id)
    except Exception:  # noqa: BLE001 - surfaced later as a friendly generation error + refund
        pass


def own_photo(s, user: User, photo_id: str) -> SourcePhoto:
    ph = s.get(SourcePhoto, photo_id)
    if not ph or s.get(Product, ph.product_id).user_id != user.id:
        raise HTTPException(404, "Photo not found")
    return ph


@router.get("/photos/{photo_id}")
def get_photo(photo_id: str, w: int | None = None, user: User = Depends(current_user), s=Depends(get_db)):
    """The original photo, or a small JPEG copy with ?w=512 for lists on slow mobile data."""
    path = storage.path_for(own_photo(s, user, photo_id).original_key)
    if not w:
        return FileResponse(path)
    from ..pipeline.prepare import load_photo
    img = load_photo(path.read_bytes())
    img.thumbnail((max(64, min(w, 1600)),) * 2)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=82)
    return Response(buf.getvalue(), media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400"})


@router.delete("/photos/{photo_id}", status_code=204)
def delete_photo(photo_id: str, user: User = Depends(current_user), s=Depends(get_db)):
    """Deletes the source photo and its cut-out. Images already generated from it stay in the
    history; their 'compare with original' view then shows that the original was deleted."""
    ph = own_photo(s, user, photo_id)
    storage.delete(ph.original_key)
    storage.delete(ph.product_key)
    for g in s.scalars(select(Generation).where(Generation.photo_id == ph.id)):
        g.photo_id = None
    s.delete(ph)
    s.commit()
