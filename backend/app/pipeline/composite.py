"""Steps 3-5: inpainting inputs, shadow, pasting the real product back, and the fidelity check."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps


def inpaint_inputs(product: Image.Image, pos: tuple[int, int], size, grow_px: int = 3):
    """Image = product on neutral grey; mask = white everywhere except the product (plus a small margin)."""
    image = Image.new("RGB", size, (128, 128, 128))
    image.paste(product, pos, product)
    alpha = Image.new("L", size, 0)
    alpha.paste(product.getchannel("A"), pos)
    keep = alpha.point(lambda v: 255 if v > 16 else 0).filter(ImageFilter.MaxFilter(2 * grow_px + 1))
    return image, ImageOps.invert(keep)


def add_contact_shadow(background: Image.Image, product: Image.Image, pos, strength: float) -> Image.Image:
    """A soft, slightly offset shadow from the product's own silhouette so it 'sits' on the surface."""
    if strength <= 0:
        return background
    size = background.size
    offset = max(1, int(product.height * 0.025))
    shadow = Image.new("L", size, 0)
    shadow.paste(product.getchannel("A"), (pos[0], pos[1] + offset))
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(1.0, product.height * 0.03)))
    shadow = shadow.point(lambda v: int(v * strength))
    dark = background.point(lambda v: int(v * 0.35))
    return Image.composite(dark, background, shadow)


def paste_product(background: Image.Image, product: Image.Image, pos) -> Image.Image:
    canvas = background.convert("RGBA")
    canvas.alpha_composite(product, dest=pos)
    return canvas.convert("RGB")


def fidelity(final: Image.Image, product: Image.Image, pos) -> float:
    """1.0 = the solid part of the product in the output is pixel-identical to the prepared source."""
    core = np.asarray(product.getchannel("A")) >= 250
    if not core.any():
        return 0.0
    x, y = pos
    region = np.asarray(final.crop((x, y, x + product.width, y + product.height))).astype(np.int16)
    source = np.asarray(product.convert("RGB")).astype(np.int16)
    return float(1.0 - np.abs(region - source)[core].mean() / 255.0)


def watermark(image: Image.Image, text: str) -> Image.Image:
    out = image.convert("RGBA")
    layer = Image.new("RGBA", out.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    try:
        from PIL import ImageFont
        font = ImageFont.load_default(size=max(14, out.width // 40))
    except TypeError:  # older Pillow
        font = None
    l, t, r, b = draw.textbbox((0, 0), text, font=font)
    m = out.width // 40
    x, y = out.width - (r - l) - m, out.height - (b - t) - m
    draw.rectangle((x - 8, y - 6, x + (r - l) + 8, y + (b - t) + 10), fill=(0, 0, 0, 90))
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 200))
    return Image.alpha_composite(out, layer).convert("RGB")
