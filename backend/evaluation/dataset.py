"""The evaluation dataset: one CSV row per example, following the spec's record template (§11.3).

The CSV opens in Excel or Google Sheets, so the founder and reviewers can maintain it without code.
Image paths are relative to the dataset folder.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from app.routes.products import CATEGORIES

COLUMNS = [
    "example_id", "physical_item_id", "category", "metal", "stone",
    "original", "extra_angles", "target", "target_same_item",
    "must_keep", "background", "intended_use",
    "rights", "confidential", "split", "tags", "limitations", "notes",
]
COLUMN_HELP = {
    "example_id": "Unique id, e.g. R001",
    "physical_item_id": "Same id for rows showing the same physical piece (optional)",
    "category": " | ".join(CATEGORIES),
    "metal": "yellow_gold, rose_gold, white_gold, silver, platinum, other (optional)",
    "stone": "e.g. diamond, ruby, kundan, pearl, none (optional)",
    "original": "Path of the phone photo, e.g. images/R001.jpg",
    "extra_angles": "More angles of the same piece, separated by ; (optional)",
    "target": "Professional reference image (optional)",
    "target_same_item": "yes | no | unknown — is the target the SAME physical piece?",
    "must_keep": "Details that must not change, separated by ; e.g. 3 stones in a row; 6 prongs; milgrain edge",
    "background": "Desired background, e.g. white, marble (optional)",
    "intended_use": "catalogue | marketplace",
    "rights": "owned | permission | unknown | none — may we process this image?",
    "confidential": "yes | no — contains customer or confidential information?",
    "split": "evaluation | development — development rows are excluded from the launch gate (§11.5)",
    "tags": "Difficulty tags separated by ; (see KNOWN_TAGS)",
    "limitations": "Known source-photo limitations, e.g. back of setting not visible",
    "notes": "Reviewer notes",
}
# §10.5 test design: what the set must cover.
KNOWN_TAGS = {
    "reflective_metal": "Reflective or polished metal",
    "matte_metal": "Matte or textured metal",
    "transparent_stone": "Transparent stones (diamond, CZ, crystal)",
    "faceted_stone": "Faceted coloured stones",
    "opaque_stone": "Opaque stones or pearls",
    "small_stones": "Many small stones / pavé",
    "fine_chain": "Fine chain or small links",
    "intricate": "Intricate design or setting",
    "simple": "Simple design",
    "good_light": "Good lighting",
    "dark": "Dark photo",
    "blurry": "Blurry photo",
    "glare": "Glare or hot reflections",
    "occluded": "Partly hidden or overlapping parts",
    "multi_angle": "Has extra angles (set automatically)",
}
RIGHTS_OK = {"owned", "permission"}


@dataclass
class Item:
    example_id: str
    category: str
    original: Path
    extra_angles: list[Path] = field(default_factory=list)
    target: Path | None = None
    must_keep: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    split: str = "evaluation"
    rights: str = "unknown"
    row: dict = field(default_factory=dict)


@dataclass
class Dataset:
    root: Path
    items: list[Item]
    errors: list[str]
    warnings: list[str]


def _split(value: str) -> list[str]:
    return [v.strip() for v in (value or "").split(";") if v.strip()]


def write_template(root: Path) -> Path:
    """Create a dataset folder with an empty CSV, a column guide, and an images/ folder."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "images").mkdir(exist_ok=True)
    csv_path = root / "items.csv"
    if not csv_path.exists():
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(COLUMNS)
    guide = ["# Column guide for items.csv", ""] + [f"- **{c}**: {h}" for c, h in COLUMN_HELP.items()]
    guide += ["", "## Difficulty tags", ""] + [f"- `{t}`: {d}" for t, d in KNOWN_TAGS.items()]
    (root / "COLUMNS.md").write_text("\n".join(guide) + "\n", encoding="utf-8")
    return csv_path


def load(root: Path) -> Dataset:
    root = Path(root)
    errors, warnings, items, seen = [], [], [], set()
    csv_path = root / "items.csv"
    if not csv_path.exists():
        return Dataset(root, [], [f"{csv_path} not found. Run: python -m evaluation init {root}"], [])
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    for n, row in enumerate(rows, start=2):
        row = {k: (v or "").strip() for k, v in row.items() if k}
        eid = row.get("example_id", "")
        where = f"row {n} ({eid or 'no id'})"
        if not eid:
            errors.append(f"{where}: example_id is empty")
            continue
        if eid in seen:
            errors.append(f"{where}: duplicate example_id")
        seen.add(eid)
        if row.get("category") not in CATEGORIES:
            errors.append(f"{where}: category must be one of {', '.join(CATEGORIES)}")
        original = root / row.get("original", "")
        if not row.get("original") or not original.is_file():
            errors.append(f"{where}: original photo not found: {row.get('original') or '(empty)'}")
        angles = [root / a for a in _split(row.get("extra_angles", ""))]
        for a in angles:
            if not a.is_file():
                errors.append(f"{where}: extra angle not found: {a.relative_to(root)}")
        target = root / row["target"] if row.get("target") else None
        if target and not target.is_file():
            warnings.append(f"{where}: target image not found: {row['target']}")
        rights = row.get("rights", "").lower() or "unknown"
        if rights not in RIGHTS_OK | {"unknown", "none"}:
            errors.append(f"{where}: rights must be owned, permission, unknown or none")
        split = row.get("split", "").lower() or "evaluation"
        if split not in ("evaluation", "development"):
            errors.append(f"{where}: split must be evaluation or development")
        tags = [t.lower() for t in _split(row.get("tags", ""))]
        for t in tags:
            if t not in KNOWN_TAGS:
                warnings.append(f"{where}: unknown tag '{t}' (kept, but not counted for coverage)")
        if angles and "multi_angle" not in tags:
            tags.append("multi_angle")
        must_keep = _split(row.get("must_keep", ""))
        if not must_keep:
            warnings.append(f"{where}: must_keep is empty; reviewers won't know which details to check")
        if row.get("confidential", "").lower() == "yes":
            warnings.append(f"{where}: marked confidential; keep this dataset out of shared drives and git")
        items.append(Item(eid, row.get("category", ""), original, angles, target, must_keep, tags,
                          split, rights, row))
    if not rows:
        errors.append("items.csv has no rows yet")
    return Dataset(root, items, errors, warnings)
