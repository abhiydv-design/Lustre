"""Quick, friendly checks so the jeweller never has to guess what went wrong.

Nothing here blocks an upload: problems become short tips shown next to the photo."""
from __future__ import annotations

import numpy as np
from PIL import Image


def photo_hints(image: Image.Image) -> list[str]:
    """Instant checks at upload time (runs in milliseconds on a downscaled copy)."""
    hints = []
    if min(image.size) < 1200:
        hints.append("This photo is small, so 4K results may look soft. Use your phone's main camera if you can.")
    gray = image.convert("L")
    gray.thumbnail((1000, 1000))
    g = np.asarray(gray).astype(np.float32)
    if g.mean() < 60:
        hints.append("This photo is quite dark. Daylight or a lamp without flash gives truer metal colour.")
    lap = np.abs(4 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:])
    if np.percentile(lap, 99.9) < 25:
        hints.append("This photo looks a little blurry. Tap on the stones to focus before shooting.")
    return hints


def cutout_hints(original_size: tuple[int, int], alpha: Image.Image) -> list[str]:
    """Checks that need the cut-out (run in the background with the first job)."""
    hints = []
    bbox = alpha.point(lambda v: 255 if v > 10 else 0).getbbox()
    if not bbox:
        return ["We couldn't find the jewellery in this photo. A plain, light background works best."]
    W, H = original_size
    margin = max(2, int(min(W, H) * 0.005))
    l, t, r, b = bbox
    if l <= margin or t <= margin or r >= W - margin or b >= H - margin:
        hints.append("Part of the piece touches the edge of the photo. Leave a little space around it.")
    if (r - l) * (b - t) < 0.02 * W * H:
        hints.append("The piece is small in the frame. Move closer for sharper detail.")
    return hints


def detect_metal(product: Image.Image) -> str:
    """Rough metal guess from the product's colours: yellow_gold, rose_gold or white_metal.

    White gold, silver and platinum look the same in a photo, so they share one label.
    The guess only guides colour handling; the jeweller can change it with one tap."""
    small = product.copy()
    small.thumbnail((400, 400))
    rgba = np.asarray(small.convert("RGBA")).astype(np.float32) / 255.0
    px = rgba[rgba[..., 3] > 0.95][:, :3]
    if len(px) < 50:
        return "white_metal"
    mx, mn = px.max(axis=1), px.min(axis=1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    r, g, b = px[:, 0], px[:, 1], px[:, 2]
    delta = np.maximum(mx - mn, 1e-6)
    hue = np.where(mx == r, ((g - b) / delta) % 6, np.where(mx == g, (b - r) / delta + 2, (r - g) / delta + 4)) * 60
    bright = mx > 0.3
    yellow = np.mean(bright & (sat > 0.3) & (hue >= 28) & (hue <= 60))
    rose = np.mean(bright & (sat > 0.15) & (sat <= 0.6) & ((hue < 25) | (hue > 345)))
    white = np.mean(bright & (sat < 0.15))
    scores = {"yellow_gold": yellow, "rose_gold": rose * 0.9, "white_metal": white * 0.8}
    return max(scores, key=scores.get)
