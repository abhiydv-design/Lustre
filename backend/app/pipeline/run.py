"""The generation pipeline: one request, one image (spec §9.4).

    source photo ─► cut-out ─► white balance ─► scene around the masked product ─► shadow
                ─► paste ORIGINAL product pixels ─► upscale scene to 4K, re-paste full-res product
                ─► pixel check ─► display preview + full-size file

The product never passes through a generative model on its way to the output. The pixel check
confirms that, but it can't catch a bad cut-out (e.g. a clear stone dropped from the mask),
so users still review every image (§9.5) and can report problems.
"""
from __future__ import annotations

import io
import json
import logging
import random

from PIL import Image
from sqlalchemy import select

from .. import credits, storage
from ..config import get_settings
from ..db import Generation, Product, SourcePhoto, new_session
from .composite import add_contact_shadow, fidelity, inpaint_inputs, paste_product
from .cutout import get_cutout
from .geometry import ASPECTS, plan, preview_size, rescale
from .inspect import cutout_hints, detect_metal
from .marketplaces import verified as verified_marketplaces
from .prepare import load_photo, prepare_product
from .providers import get_scene_provider, get_upscaler
from .styles import STYLES

log = logging.getLogger("studio.pipeline")
MIN_PIXEL_MATCH = 0.995


def _providers():
    s = get_settings()
    return (get_cutout(s.cutout_provider, s.rembg_model),
            get_scene_provider(s.scene_provider, s.flux_fill_model),
            get_upscaler(s.upscale_provider, s.esrgan_model))


def _set(gen_id: str, **fields) -> None:
    with new_session() as s:
        g = s.get(Generation, gen_id)
        for k, v in fields.items():
            setattr(g, k, v)
        s.commit()


def ensure_prepared(photo_id: str) -> Image.Image:
    """Cut out and colour-correct a source photo once; reused by every later generation."""
    with new_session() as s:
        photo = s.get(SourcePhoto, photo_id)
        if photo.product_key:
            return storage.load_image(photo.product_key)
        original = load_photo(storage.path_for(photo.original_key).read_bytes())
        cutout_fn, _, _ = _providers()
        cutout = cutout_fn(original)
        photo.hints = json.dumps(json.loads(photo.hints or "[]") + cutout_hints(original.size, cutout.getchannel("A")))
        s.commit()
        product_img, info = prepare_product(original, cutout, get_settings().white_balance_strength)
        photo.product_key = storage.save_image(f"products/{photo.product_id}/{photo.id}_cutout.png", product_img)
        product = s.get(Product, photo.product_id)
        if not product.metal:
            product.metal, product.metal_source = detect_metal(product_img), "detected"
        s.commit()
        log.info("prepared photo %s %s", photo_id, info)
        return product_img


def target(g: Generation) -> tuple[tuple[int, int], float, str, str]:
    """(canvas size, fill, style id, file format) for a generation."""
    if g.output == "marketplace":
        mp = verified_marketplaces()[g.marketplace_preset]
        fmt = "png" if "png" in mp.formats else mp.formats[0]
        return (mp.width, mp.height), mp.fill, mp.style, fmt
    return ASPECTS[g.aspect], 0.62, g.preset, "png"


def render(product: Image.Image, style_id: str, canvas: tuple[int, int], fill: float, seed: int, on_stage=None):
    stage = on_stage or (lambda _: None)
    style = STYLES[style_id]
    _, scene_provider, upscaler = _providers()

    stage("scene")
    size = preview_size(canvas, get_settings().preview_long_side)
    full = plan(product.size, canvas, fill=fill)
    p = rescale(full, size)
    small = product.resize((p.w, p.h), Image.LANCZOS)
    if style.flat_color:
        scene = Image.new("RGB", size, style.flat_color)
    else:
        image, mask = inpaint_inputs(small, (p.x, p.y), size)
        scene = scene_provider.generate(image, mask, style, seed, size)

    stage("lighting")
    preview = paste_product(add_contact_shadow(scene, small, (p.x, p.y), style.shadow), small, (p.x, p.y))
    preview_score = fidelity(preview, small, (p.x, p.y))

    stage("upscale")
    background = Image.new("RGB", canvas, style.flat_color) if style.flat_color else upscaler.upscale(scene, canvas)
    placed = product if product.size == (full.w, full.h) else product.resize((full.w, full.h), Image.LANCZOS)
    final = paste_product(add_contact_shadow(background, placed, (full.x, full.y), style.shadow), placed, (full.x, full.y))
    final_score = fidelity(final, placed, (full.x, full.y))

    warning = None
    if full.scale > 1.05:
        warning = (f"Your photo was enlarged {full.scale:.1f}x for this size, so fine detail may look soft. "
                   "Shoot closer, or use the main (1x) camera, for the crispest result.")
    return scene, preview, final, min(preview_score, final_score), warning


def friendly_error(exc: Exception) -> str:
    text = str(exc)
    if "No jewellery found" in text:
        return "We couldn't find the jewellery in your photo. Try again on a plain, light background. Your credit has been returned."
    if "pixel check" in text:
        return "The result didn't match your photo closely enough, so we stopped. Your credit has been returned."
    return "Something went wrong on our side. Your credit has been returned; please try again."


def _encode(final: Image.Image, fmt: str, max_mb: float | None) -> tuple[bytes, str]:
    if fmt == "png":
        buf = io.BytesIO()
        final.save(buf, format="PNG")
        return buf.getvalue(), "png"
    for quality in (95, 90, 85, 80, 75):
        buf = io.BytesIO()
        final.save(buf, format="JPEG", quality=quality, subsampling=0 if quality >= 90 else 2)
        if not max_mb or buf.tell() <= max_mb * 1024 * 1024:
            break
    return buf.getvalue(), "jpg"


def refund_failed(gen_id: str, message: str) -> None:
    with new_session() as s:
        g = s.get(Generation, gen_id)
        g.status, g.message = "failed", message
        user_id, cost = g.user_id, g.cost
        s.commit()
        if cost:
            credits.apply(s, user_id, +cost, "refund_technical", f"refund:generation:{gen_id}",
                          note="Generation failed")


def process_generation(gen_id: str) -> None:
    """Runs in the background after POST /products/{id}/generations."""
    try:
        _set(gen_id, status="running", stage="cutout")
        with new_session() as s:
            g = s.get(Generation, gen_id)
            photo_id, product_id = g.photo_id, g.product_id
            canvas, fill, style_id, fmt = target(g)
            max_mb = verified_marketplaces()[g.marketplace_preset].max_file_mb if g.output == "marketplace" else None
        product = ensure_prepared(photo_id)
        seed = random.Random().randrange(1, 2**31 - 1)
        scene, preview, final, score, warning = render(
            product, style_id, canvas, fill, seed, on_stage=lambda st: _set(gen_id, stage=st))
        if score < MIN_PIXEL_MATCH:
            raise RuntimeError(f"pixel check failed ({score:.4f})")
        base = f"products/{product_id}/gen_{gen_id}"
        data, ext = _encode(final, fmt, max_mb)
        _set(gen_id, status="done", stage="ready", seed=seed, fidelity=score, warning=warning,
             width=final.width, height=final.height,
             scene_key=storage.save_image(f"{base}_scene.png", scene),
             preview_key=storage.save_image(f"{base}_preview.jpg", preview, quality=88),
             final_key=storage.save_bytes(f"{base}_full.{ext}", data))
    except Exception as exc:  # noqa: BLE001 - every failure must refund
        log.exception("generation %s failed", gen_id)
        refund_failed(gen_id, friendly_error(exc))


def recover_interrupted() -> int:
    """On startup, fail and refund generations a crash or restart left unfinished (spec §19:
    interrupted requests must not create lost charges). Single-process MVP only: with several
    workers, move this to the job queue's own retry/timeout handling."""
    with new_session() as s:
        ids = list(s.scalars(select(Generation.id).where(Generation.status.in_(("queued", "running")))))
    for gid in ids:
        refund_failed(gid, "This generation was interrupted. Your credit has been returned; please try again.")
    return len(ids)
