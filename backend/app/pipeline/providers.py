"""AI providers behind small interfaces, so models can be swapped (Replicate, fal.ai, self-hosted)
without touching the pipeline. Mock providers let everything run offline and in tests."""
from __future__ import annotations

import io
from functools import lru_cache

import httpx
import numpy as np
from PIL import Image

from .styles import Style


def _png(image: Image.Image, name: str) -> io.BytesIO:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    buf.name = name
    return buf


def _read_replicate_output(out) -> bytes:
    if isinstance(out, (list, tuple)):
        out = out[0]
    if hasattr(out, "read"):  # replicate>=1.0 returns FileOutput
        return out.read()
    response = httpx.get(str(out), timeout=180, follow_redirects=True)
    response.raise_for_status()
    return response.content


# ---------- Scene generation (background only) ----------

class MockScene:
    """Seeded two-colour gradient with light grain. No network, no cost."""

    def generate(self, image, mask, style: Style, seed: int, size) -> Image.Image:
        rng = np.random.default_rng(seed)
        W, H = size
        angle = rng.uniform(0, np.pi)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        t = (xx / W) * np.cos(angle) + (yy / H) * np.sin(angle)
        t = (t - t.min()) / max(1e-6, float(t.max() - t.min()))
        c0, c1 = (np.array(c, np.float32) for c in style.mock_colors)
        arr = c0 * (1 - t[..., None]) + c1 * t[..., None]
        arr += rng.normal(0, 2.0, arr.shape)
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


class ReplicateFluxFill:
    """Inpaints everything outside the product mask (FLUX.1 Fill).
    Mask: white = generate, black = keep."""

    def __init__(self, model: str):
        self.model = model

    def generate(self, image, mask, style: Style, seed: int, size) -> Image.Image:
        import replicate
        out = replicate.run(self.model, input={
            "image": _png(image, "image.png"),
            "mask": _png(mask, "mask.png"),
            "prompt": style.prompt,
            "seed": seed,
            "output_format": "png",
        })
        scene = Image.open(io.BytesIO(_read_replicate_output(out))).convert("RGB")
        return scene.resize(size, Image.LANCZOS)


# ---------- Upscaling (background only; the product is re-pasted at full resolution) ----------

class LanczosUpscaler:
    def upscale(self, image: Image.Image, size) -> Image.Image:
        return image.resize(size, Image.LANCZOS)


class ReplicateESRGAN:
    def __init__(self, model: str):
        self.model = model

    def upscale(self, image: Image.Image, size) -> Image.Image:
        import replicate
        factor = max(2, min(4, int(np.ceil(max(size[0] / image.width, size[1] / image.height)))))
        out = replicate.run(self.model, input={
            "image": _png(image, "scene.png"),
            "scale": factor,
            "face_enhance": False,
        })
        big = Image.open(io.BytesIO(_read_replicate_output(out))).convert("RGB")
        return big.resize(size, Image.LANCZOS)


@lru_cache
def get_scene_provider(name: str, flux_model: str):
    if name == "mock":
        return MockScene()
    if name == "replicate":
        return ReplicateFluxFill(flux_model)
    raise ValueError(f"unknown SCENE_PROVIDER {name!r}")


@lru_cache
def get_upscaler(name: str, esrgan_model: str):
    if name == "lanczos":
        return LanczosUpscaler()
    if name == "replicate":
        return ReplicateESRGAN(esrgan_model)
    raise ValueError(f"unknown UPSCALE_PROVIDER {name!r}")
