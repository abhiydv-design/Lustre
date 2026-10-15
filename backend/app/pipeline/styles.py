"""Style presets shown on the 'Choose a look' screen.

Every prompt describes ONLY the scene. The jewellery itself is never generated:
the original pixels are pasted back on top after the scene is made.
"""
from __future__ import annotations

from dataclasses import dataclass

_SCENE_ONLY = (
    " The jewellery piece already in the image must stay exactly as it is. "
    "Photorealistic, sharp, high-end commercial product photography, no text, no watermark, no hands."
)


@dataclass(frozen=True)
class Style:
    id: str
    label: str
    prompt: str
    shadow: float               # strength of the synthetic contact shadow, 0-1
    mock_colors: tuple[tuple[int, int, int], tuple[int, int, int]]
    deterministic_color: tuple[int, int, int] | None = None  # no AI: flat studio background
    available: bool = True


STYLES: dict[str, Style] = {s.id: s for s in [
    Style(
        id="white", label="White catalog",
        prompt="",
        shadow=0.30,
        mock_colors=((255, 255, 255), (255, 255, 255)),
        deterministic_color=(255, 255, 255),  # pure #FFFFFF, as marketplaces require
    ),
    Style(
        id="marble", label="Marble",
        prompt=("A jewellery piece resting on polished white Carrara marble with soft grey veining, "
                "soft diffused studio light from the upper left, gentle natural contact shadow, "
                "shallow depth of field, clean luxurious mood." + _SCENE_ONLY),
        shadow=0.22,
        mock_colors=((244, 242, 238), (217, 211, 202)),
    ),
    Style(
        id="velvet", label="Velvet tray",
        prompt=("A jewellery piece resting on a deep plum velvet jewellery tray, soft warm spotlight, "
                "rich fabric texture, subtle vignette, classic showroom mood." + _SCENE_ONLY),
        shadow=0.30,
        mock_colors=((67, 36, 74), (29, 15, 32)),
    ),
    Style(
        id="silk", label="Silk drape",
        prompt=("A jewellery piece resting on softly draped champagne silk with gentle folds, "
                "warm diffused daylight, soft and elegant mood." + _SCENE_ONLY),
        shadow=0.20,
        mock_colors=((243, 227, 211), (215, 181, 150)),
    ),
    Style(
        id="festive", label="Festive",
        prompt=("A jewellery piece on a rich maroon surface, softly blurred marigold flowers and warm "
                "diya lights as bokeh in the background, Indian festive mood, warm golden light." + _SCENE_ONLY),
        shadow=0.28,
        mock_colors=((138, 42, 30), (59, 11, 11)),
    ),
    Style(
        id="on_model", label="On model",
        prompt="",
        shadow=0.0,
        mock_colors=((201, 162, 138), (156, 117, 99)),
        available=False,  # phase 2: needs pose-aware placement and occlusion
    ),
]}
