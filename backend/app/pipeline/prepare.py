"""Non-generative clean-up of the real product pixels: orientation, cut-out crop,
and a gentle white-balance correction. Nothing here invents detail."""
from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageOps

MAX_SOURCE_SIDE = 6000

try:  # iPhone HEIC support, if installed
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:  # pragma: no cover
    pass


def load_photo(data: bytes) -> Image.Image:
    """Decode an upload, apply the phone's EXIF rotation, return RGB."""
    image = Image.open(io.BytesIO(data))
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")
    if max(image.size) > MAX_SOURCE_SIDE:
        image.thumbnail((MAX_SOURCE_SIDE, MAX_SOURCE_SIDE), Image.LANCZOS)
    return image


def white_balance_gains(rgb: Image.Image, alpha: Image.Image, strength: float = 0.5,
                        clamp: float = 0.08) -> tuple[float, float, float]:
    """Use the photo's own (meant-to-be-white) background as a grey card.

    Phone photos under warm bulbs turn white gold yellow and yellow gold orange.
    If the background is light enough to be a reference, scale each channel towards neutral.

    Caution: a cream or tinted backdrop looks exactly like white paper under warm light, and
    fully neutralising it turns silver and white gold blue (found by the evaluation harness,
    demo item D002). So the correction is partial (`strength`, 0 = off, 1 = full) and clamped.
    Tune WHITE_BALANCE_STRENGTH with the evaluation harness rather than by eye.
    """
    small = rgb.copy()
    small.thumbnail((800, 800))
    a = np.asarray(alpha.resize(small.size, Image.BILINEAR))
    px = np.asarray(small).reshape(-1, 3)[a.reshape(-1) < 8].astype(np.float64)
    if len(px) < 500:
        return 1.0, 1.0, 1.0
    mean = px.mean(axis=0)
    if mean.mean() < 110:
        return 1.0, 1.0, 1.0
    full = mean.mean() / np.maximum(mean, 1.0)
    gains = np.clip(1.0 + strength * (full - 1.0), 1 - clamp, 1 + clamp)
    return tuple(float(g) for g in gains)


def apply_gains(rgba: Image.Image, gains: tuple[float, float, float]) -> Image.Image:
    if all(abs(g - 1.0) < 1e-3 for g in gains):
        return rgba
    r, g, b, a = rgba.split()
    channels = [c.point(lambda v, k=k: min(255, int(v * k + 0.5))) for c, k in zip((r, g, b), gains)]
    return Image.merge("RGBA", (*channels, a))


def crop_to_content(rgba: Image.Image, pad: float = 0.01) -> Image.Image:
    bbox = rgba.getchannel("A").point(lambda v: 255 if v > 10 else 0).getbbox()
    if not bbox:
        raise ValueError("No jewellery found in this photo. Try a plainer background.")
    l, t, r, b = bbox
    p = int(max(r - l, b - t) * pad)
    W, H = rgba.size
    return rgba.crop((max(0, l - p), max(0, t - p), min(W, r + p), min(H, b + p)))


def prepare_product(original: Image.Image, cutout: Image.Image,
                    wb_strength: float = 0.5) -> tuple[Image.Image, dict]:
    gains = white_balance_gains(original, cutout.getchannel("A"), strength=wb_strength)
    product = crop_to_content(apply_gains(cutout, gains))
    return product, {"white_balance_gains": gains}
