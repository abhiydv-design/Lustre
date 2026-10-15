"""A small synthetic dataset so the whole evaluation loop can be tried before real photos exist.
These are drawings, not jewellery photos: use them to learn the tool, never to judge quality."""
from __future__ import annotations

import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from .dataset import COLUMNS, write_template


def _canvas(bg=(238, 229, 212), size=(2000, 1500)):
    img = Image.new("RGB", size, bg)
    return img, ImageDraw.Draw(img)


def _ring(path: Path, metal=(196, 150, 60), stone=(40, 90, 170), dark=False, blur=False):
    img, d = _canvas((120, 112, 100) if dark else (238, 229, 212))
    cx, cy, r = 1000, 820, 300
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=metal, width=75)
    d.polygon([(cx - 140, cy - r - 30), (cx - 70, cy - r - 160), (cx + 70, cy - r - 160),
               (cx + 140, cy - r - 30), (cx, cy - r + 90)], fill=stone, outline=(30, 40, 60))
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(6))
    img.save(path, quality=95)


def _pendant(path: Path):
    img, d = _canvas()
    for i in range(0, 60):  # fine chain of small links
        x = 400 + i * 20
        y = 300 + int(((i - 30) ** 2) * 0.45)
        d.ellipse((x, y, x + 14, y + 8), outline=(200, 160, 150), width=3)
    d.polygon([(1000, 760), (1110, 900), (1000, 1100), (890, 900)], fill=(170, 30, 60), outline=(90, 10, 30))
    img.save(path, quality=95)


def _earrings(path: Path, angle=False):
    img, d = _canvas()
    for cx in ((700, 1300) if not angle else (850, 1150)):
        d.ellipse((cx - 50, 450, cx + 50, 550), fill=(245, 245, 240), outline=(190, 190, 190), width=6)  # pearl
        d.line((cx, 550, cx, 700), fill=(200, 200, 205), width=8)
        d.ellipse((cx - 70, 700, cx + 70, 860), outline=(200, 200, 205), width=14)
    img.save(path, quality=95)


def make_demo(root: Path) -> Path:
    write_template(root)
    img = root / "images"
    _ring(img / "D001.jpg")
    _ring(img / "D002.jpg", metal=(205, 205, 210), stone=(235, 240, 245))
    _ring(img / "D003.jpg", dark=True, blur=True)
    _pendant(img / "D004.jpg")
    _earrings(img / "D005.jpg")
    _earrings(img / "D005_side.jpg", angle=True)
    rows = [
        ["D001", "demo-ring-1", "ring", "yellow_gold", "sapphire", "images/D001.jpg", "", "", "unknown",
         "one blue stone; four facets visible; plain band", "white", "catalogue", "owned", "no", "evaluation",
         "reflective_metal;faceted_stone;simple;good_light", "", "synthetic drawing"],
        ["D002", "demo-ring-2", "ring", "white_gold", "diamond", "images/D002.jpg", "", "", "unknown",
         "one clear stone; band thickness", "white", "catalogue", "owned", "no", "evaluation",
         "reflective_metal;transparent_stone;simple", "", "clear stone close to background colour"],
        ["D003", "demo-ring-1", "ring", "yellow_gold", "sapphire", "images/D003.jpg", "", "", "unknown",
         "one blue stone", "marble", "catalogue", "owned", "no", "evaluation",
         "dark;blurry", "very dark and soft", "same item as D001, poor photo"],
        ["D004", "demo-pendant", "pendant", "rose_gold", "ruby", "images/D004.jpg", "", "", "unknown",
         "60 chain links; one red stone; stone below chain centre", "marble", "catalogue", "owned", "no",
         "evaluation", "fine_chain;faceted_stone;intricate", "", "fine links test the cut-out"],
        ["D005", "demo-earrings", "earrings", "silver", "pearl", "images/D005.jpg", "images/D005_side.jpg", "",
         "unknown", "two pearls; two hoops; equal length", "white", "catalogue", "owned", "no", "development",
         "opaque_stone;occluded", "back of hoops not visible", "development example: excluded from the gate"],
    ]
    with (root / "items.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        w.writerows(rows)
    return root
