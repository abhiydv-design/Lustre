"""The orchestrator.

    upload ──► cut-out ──► white balance ──► (preview) scene around the product ──► shadow
           ──► paste ORIGINAL product pixels ──► fidelity check ──► free watermarked preview

    download (1 credit) ──► upscale the SCENE to 4K ──► paste full-resolution product ──► check ──► PNG

The product is never passed through a generative model on its way to the output.
"""
from __future__ import annotations

import logging
import random

from PIL import Image
from sqlalchemy import select

from .. import credits, storage
from ..config import get_settings
from ..db import Job, SourcePhoto, Variation, new_session
from .composite import add_contact_shadow, fidelity, inpaint_inputs, paste_product, watermark
from .cutout import get_cutout
from .geometry import FORMATS, plan, preview_size, rescale
from .prepare import load_photo, prepare_product
from .providers import get_scene_provider, get_upscaler
from .styles import STYLES

log = logging.getLogger("lustre.pipeline")
MIN_FIDELITY = 0.995


def _providers():
    s = get_settings()
    return (get_cutout(s.cutout_provider, s.rembg_model),
            get_scene_provider(s.scene_provider, s.flux_fill_model),
            get_upscaler(s.upscale_provider, s.esrgan_model))


def _set(job_id: str, **fields) -> None:
    with new_session() as s:
        job = s.get(Job, job_id)
        for k, v in fields.items():
            setattr(job, k, v)
        s.commit()


def ensure_prepared(photo_id: str) -> Image.Image:
    with new_session() as s:
        photo = s.get(SourcePhoto, photo_id)
        if photo.product_key:
            return storage.load_image(photo.product_key)
        original = load_photo(storage.path_for(photo.original_key).read_bytes())
        cutout_fn, _, _ = _providers()
        product, info = prepare_product(original, cutout_fn(original))
        photo.product_key = storage.save_image(f"shoots/{photo.shoot_id}/{photo.id}_product.png", product)
        s.commit()
        log.info("prepared photo %s %s", photo_id, info)
        return product


def render_preview(product: Image.Image, style_id: str, fmt: str, seed: int):
    settings = get_settings()
    style = STYLES[style_id]
    _, scene_provider, _ = _providers()
    size = preview_size(fmt, settings.preview_long_side)
    p = rescale(plan(product.size, fmt), size)
    small = product.resize((p.w, p.h), Image.LANCZOS)
    if style.deterministic_color:
        scene = Image.new("RGB", size, style.deterministic_color)
    else:
        image, mask = inpaint_inputs(small, (p.x, p.y), size)
        scene = scene_provider.generate(image, mask, style, seed, size)
    composed = paste_product(add_contact_shadow(scene, small, (p.x, p.y), style.shadow), small, (p.x, p.y))
    score = fidelity(composed, small, (p.x, p.y))
    return scene, composed, score


def render_final(product: Image.Image, scene: Image.Image, style_id: str, fmt: str):
    style = STYLES[style_id]
    _, _, upscaler = _providers()
    p = plan(product.size, fmt)
    background = (Image.new("RGB", FORMATS[fmt], style.deterministic_color) if style.deterministic_color
                  else upscaler.upscale(scene, FORMATS[fmt]))
    placed = product if product.size == (p.w, p.h) else product.resize((p.w, p.h), Image.LANCZOS)
    final = paste_product(add_contact_shadow(background, placed, (p.x, p.y), style.shadow), placed, (p.x, p.y))
    warning = None
    if p.scale > 1.05:
        warning = (f"Your photo was enlarged {p.scale:.1f}x to reach 4K, so fine detail may look soft. "
                   "Shoot closer, or use the main (1x) camera, for the crispest result.")
    return final, fidelity(final, placed, (p.x, p.y)), warning


def process_job(job_id: str) -> None:
    """Runs in the background after POST /shoots/{id}/jobs."""
    settings = get_settings()
    try:
        _set(job_id, status="running", stage="cutout")
        with new_session() as s:
            job = s.get(Job, job_id)
            photo_ids = list(s.scalars(
                select(SourcePhoto.id).where(SourcePhoto.shoot_id == job.shoot_id).order_by(SourcePhoto.position)
            ))
            style_id, fmt, count = job.style, job.fmt, job.count
        products = {pid: ensure_prepared(pid) for pid in photo_ids}

        _set(job_id, stage="scene")
        rng = random.Random()
        for i in range(count):
            pid = photo_ids[i % len(photo_ids)]  # spread variations across the uploaded angles
            seed = rng.randrange(1, 2**31 - 1)
            scene, preview, score = render_preview(products[pid], style_id, fmt, seed)
            if score < MIN_FIDELITY:
                raise RuntimeError(f"fidelity check failed on preview ({score:.4f})")
            if i == 0:
                _set(job_id, stage="lighting")
            base = f"jobs/{job_id}/{i}_{seed}"
            scene_key = storage.save_image(f"{base}_scene.png", scene)
            if settings.preview_watermark:
                preview = watermark(preview, f"PREVIEW · {settings.brand_name}")
            preview_key = storage.save_image(f"{base}_preview.jpg", preview, quality=88)
            with new_session() as s:
                s.add(Variation(job_id=job_id, photo_id=pid, position=i, seed=seed,
                                scene_key=scene_key, preview_key=preview_key, preview_fidelity=score))
                s.commit()
        _set(job_id, status="done", stage="ready")
    except Exception as exc:  # noqa: BLE001 - surface any failure to the app
        log.exception("job %s failed", job_id)
        _set(job_id, status="failed", error=str(exc)[:500])


def process_final(variation_id: str, charge_ref: str) -> None:
    """Runs in the background after a paid download. Refunds the credit if rendering fails."""
    with new_session() as s:
        v = s.get(Variation, variation_id)
        job = s.get(Job, v.job_id)
        user_id, style_id, fmt, photo_id, scene_key = job.user_id, job.style, job.fmt, v.photo_id, v.scene_key
    try:
        product = ensure_prepared(photo_id)
        final, score, warning = render_final(product, storage.load_image(scene_key).convert("RGB"), style_id, fmt)
        if score < MIN_FIDELITY:
            raise RuntimeError(f"fidelity check failed on 4K render ({score:.4f})")
        key = storage.save_image(f"jobs/{v.job_id}/{variation_id}_4k.png", final, optimize=False)
        with new_session() as s:
            v = s.get(Variation, variation_id)
            v.final_key, v.final_status, v.final_fidelity, v.warning = key, "ready", score, warning
            s.commit()
    except Exception:  # noqa: BLE001
        log.exception("4K render failed for %s", variation_id)
        with new_session() as s:
            s.get(Variation, variation_id).final_status = "failed"
            s.commit()
            credits.apply(s, user_id, +1, "refund", f"refund:{charge_ref}")
