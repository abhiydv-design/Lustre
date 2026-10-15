"""Visual presets (spec §9.4).

Version 1 covers catalogue and marketplace imagery only (§7). Luxury, lifestyle and model-worn
looks are defined but switched off until they can be evaluated for fidelity (§7.2, §17).

Every prompt describes ONLY the scene. The jewellery is never generated: the original pixels
are pasted back on top after the scene is made.
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
    label_hi: str
    group: str                  # catalogue | luxury | lifestyle
    prompt: str
    shadow: float               # strength of the synthetic contact shadow, 0-1
    mock_colors: tuple[tuple[int, int, int], tuple[int, int, int]]
    flat_color: tuple[int, int, int] | None = None  # no AI needed: plain studio background
    available: bool = True


STYLES: dict[str, Style] = {s.id: s for s in [
    Style("white", "White", "सफ़ेद", "catalogue", "", 0.30,
          ((255, 255, 255), (255, 255, 255)), flat_color=(255, 255, 255)),
    Style("grey", "Soft grey", "हल्का ग्रे", "catalogue", "", 0.28,
          ((236, 236, 236), (236, 236, 236)), flat_color=(236, 236, 236)),
    Style("beige", "Warm beige", "हल्का बेज", "catalogue",
          "A jewellery piece on a plain warm beige paper sweep, soft even studio light, "
          "gentle natural contact shadow, clean minimal catalogue look." + _SCENE_ONLY,
          0.24, ((242, 234, 222), (228, 216, 198))),
    Style("marble", "Marble", "मार्बल", "catalogue",
          "A jewellery piece resting on polished white Carrara marble with soft grey veining, "
          "soft diffused studio light from the upper left, gentle natural contact shadow, "
          "clean catalogue look." + _SCENE_ONLY,
          0.22, ((244, 242, 238), (217, 211, 202))),
    # ----- Deferred to later releases (§7.2) -----
    Style("velvet", "Velvet tray", "मखमल ट्रे", "luxury",
          "A jewellery piece on a deep plum velvet jewellery tray, soft warm spotlight." + _SCENE_ONLY,
          0.30, ((67, 36, 74), (29, 15, 32)), available=False),
    Style("silk", "Silk drape", "रेशमी कपड़ा", "lifestyle",
          "A jewellery piece on softly draped champagne silk, warm daylight." + _SCENE_ONLY,
          0.20, ((243, 227, 211), (215, 181, 150)), available=False),
    Style("festive", "Festive", "त्योहार", "lifestyle",
          "A jewellery piece on a maroon surface with blurred marigolds and diya bokeh." + _SCENE_ONLY,
          0.28, ((138, 42, 30), (59, 11, 11)), available=False),
    Style("on_model", "On model", "मॉडल पर", "lifestyle", "", 0.0,
          ((201, 162, 138), (156, 117, 99)), available=False),
]}
