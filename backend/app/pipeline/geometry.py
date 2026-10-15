"""Output formats and where the product sits on the canvas."""
from __future__ import annotations

from dataclasses import dataclass

FORMATS: dict[str, tuple[int, int]] = {
    "1:1": (3840, 3840),   # marketplaces
    "4:5": (3072, 3840),   # Instagram portrait
    "16:9": (3840, 2160),  # web banner (4K UHD)
}


@dataclass(frozen=True)
class Placement:
    canvas: tuple[int, int]
    x: int
    y: int
    w: int
    h: int
    scale: float  # placed pixels per source pixel (>1 means the photo is being enlarged)


def plan(product_size: tuple[int, int], fmt: str, fill: float = 0.62, center_y: float = 0.53) -> Placement:
    """Fit the product into the final 4K canvas, centred and slightly low (reads as 'resting')."""
    W, H = FORMATS[fmt]
    pw, ph = product_size
    box_h = fill * min(W, H)
    box_w = box_h if W <= H else min(W * 0.8, box_h * 1.6)
    s = min(box_w / pw, box_h / ph)
    w, h = max(1, round(pw * s)), max(1, round(ph * s))
    x = round((W - w) / 2)
    y = min(max(0, round(H * center_y - h / 2)), H - h)
    return Placement((W, H), x, y, w, h, s)


def rescale(p: Placement, size: tuple[int, int]) -> Placement:
    fx, fy = size[0] / p.canvas[0], size[1] / p.canvas[1]
    return Placement(size, round(p.x * fx), round(p.y * fy),
                     max(1, round(p.w * fx)), max(1, round(p.h * fy)), p.scale * fx)


def preview_size(fmt: str, long_side: int) -> tuple[int, int]:
    """Preview canvas with the same aspect, sides rounded to multiples of 16 (diffusion models like that)."""
    W, H = FORMATS[fmt]
    k = long_side / max(W, H)
    return max(16, round(W * k / 16) * 16), max(16, round(H * k / 16) * 16)
