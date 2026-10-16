"""Step 1: separate the jewellery from its background (alpha mask, original pixels)."""
from __future__ import annotations

from functools import lru_cache

import numpy as np
from PIL import Image, ImageFilter


class ThresholdCutout:
    """Dependency-free fallback for photos on a plain, light background (lightbox / white sheet).
    It struggles with clear or white stones; use rembg/BiRefNet in production."""

    name = "threshold"

    def __call__(self, image: Image.Image) -> Image.Image:
        work = image.copy()
        work.thumbnail((1500, 1500))
        arr = np.asarray(work).astype(np.float32)
        b = max(2, min(arr.shape[:2]) // 50)
        border = np.concatenate([arr[:b].reshape(-1, 3), arr[-b:].reshape(-1, 3),
                                 arr[:, :b].reshape(-1, 3), arr[:, -b:].reshape(-1, 3)])
        background = np.median(border, axis=0)
        distance = np.sqrt(((arr - background) ** 2).sum(axis=-1))
        alpha = np.clip((distance - 18.0) / 24.0, 0.0, 1.0)
        mask = Image.fromarray((alpha * 255).astype(np.uint8))
        mask = mask.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))  # close small holes
        mask = mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))  # drop dust specks
        mask = mask.resize(image.size, Image.BILINEAR).filter(ImageFilter.GaussianBlur(0.8))
        out = image.convert("RGBA")
        out.putalpha(mask)
        return out


class RembgCutout:
    """AI cut-out via rembg, on CPU. Memory measured on a 4 GB, 1-CPU machine with a 2400×1800 photo:
    - isnet-general-use (default): ~1.3 GB peak, ~3 s per photo. Fits a 2 GB server.
    - birefnet-general: finer edges on chains and prongs, but went past 2.7 GB and was killed.
      Use it only on servers with 6 GB+ of memory, and compare both with the evaluation harness.
    The model stays loaded after first use, so the server keeps that memory."""

    name = "rembg"

    def __init__(self, model: str):
        from rembg import new_session
        self.session = new_session(model)

    def __call__(self, image: Image.Image) -> Image.Image:
        from rembg import remove
        return remove(image, session=self.session, post_process_mask=True).convert("RGBA")


@lru_cache
def get_cutout(provider: str, rembg_model: str):
    if provider == "rembg":
        return RembgCutout(rembg_model)
    if provider == "threshold":
        return ThresholdCutout()
    raise ValueError(f"unknown CUTOUT_PROVIDER {provider!r}")
