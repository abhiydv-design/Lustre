"""Run every dataset example through the production pipeline and record what happened (§10.5)."""
from __future__ import annotations

import json
import os
import random
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from app.config import get_settings
from app.pipeline.cutout import get_cutout
from app.pipeline.geometry import ASPECTS
from app.pipeline.inspect import photo_hints
from app.pipeline.prepare import load_photo, prepare_product
from app.pipeline.run import MIN_PIXEL_MATCH, render
from app.pipeline.styles import STYLES

from .dataset import RIGHTS_OK, Dataset

REVIEW_SIDE = 1600


def uses_external_processing() -> bool:
    s = get_settings()
    return s.scene_provider != "mock" or s.upscale_provider != "lanczos"


def _git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                              cwd=Path(__file__).parent, timeout=5).stdout.strip() or None
    except Exception:  # noqa: BLE001
        return None


def _review_copy(img: Image.Image, path: Path) -> str:
    small = img.convert("RGB")
    small.thumbnail((REVIEW_SIDE, REVIEW_SIDE), Image.LANCZOS)
    small.save(path, quality=90)
    return path.name


def _cost(calls: dict) -> float | None:
    """Estimated provider cost in USD, if per-call prices are set (§10.5: 'once measurable')."""
    prices = {"scene": os.environ.get("EVAL_SCENE_COST_USD"), "upscale": os.environ.get("EVAL_UPSCALE_COST_USD")}
    if not any(prices.values()):
        return None
    return round(sum(calls[k] * float(prices[k] or 0) for k in calls), 4)


def run(dataset: Dataset, out_dir: Path, name: str, presets: list[str], aspect: str = "1:1",
        repeats: int = 1, allow_unverified_rights: bool = False, log=print) -> Path:
    if dataset.errors:
        raise ValueError("Fix the dataset first:\n- " + "\n- ".join(dataset.errors))
    for p in presets:
        if p not in STYLES:
            raise ValueError(f"Unknown preset {p!r}. Options: {', '.join(STYLES)}")
    if aspect not in ASPECTS:
        raise ValueError(f"Unknown aspect {aspect!r}. Options: {', '.join(ASPECTS)}")
    external = uses_external_processing()
    blocked = [i.example_id for i in dataset.items if i.rights not in RIGHTS_OK]
    if external and blocked and not allow_unverified_rights:
        raise PermissionError(
            "These examples don't have confirmed image rights (owned/permission), and this run sends "
            f"images to an external AI provider (§11.4): {', '.join(blocked)}. Fix the rights column, "
            "or use mock providers.")

    run_dir = out_dir / name
    if run_dir.exists():
        raise FileExistsError(f"Run '{name}' already exists at {run_dir}. Pick a new name.")
    images = run_dir / "images"
    images.mkdir(parents=True)
    s = get_settings()
    cutout = get_cutout(s.cutout_provider, s.rembg_model)
    canvas = ASPECTS[aspect]

    results = []
    for item in dataset.items:
        original = load_photo(item.original.read_bytes())
        orig_name = _review_copy(original, images / f"{item.example_id}_original.jpg")
        target_name = _review_copy(load_photo(item.target.read_bytes()), images / f"{item.example_id}_target.jpg") \
            if item.target and item.target.is_file() else None
        hints = photo_hints(original)
        prepared, prep_error = None, None
        t0 = time.perf_counter()
        try:
            prepared, _ = prepare_product(original, cutout(original), s.white_balance_strength)
        except Exception as exc:  # noqa: BLE001
            prep_error = str(exc)
        prep_seconds = time.perf_counter() - t0

        for preset in presets:
            for rep in range(1, repeats + 1):
                oid = f"{item.example_id}__{preset}__{rep}"
                seed = random.Random(f"{name}:{oid}").randrange(1, 2**31 - 1)  # reproducible per run name
                flat = STYLES[preset].flat_color is not None
                calls = {"scene": 0 if flat else 1, "upscale": 0 if flat else 1}
                rec = {"output_id": oid, "example_id": item.example_id, "preset": preset, "aspect": aspect,
                       "repeat": rep, "seed": seed, "split": item.split, "category": item.category,
                       "tags": item.tags, "photo_hints": hints, "status": "ok", "error": None,
                       "seconds": None, "provider_calls": calls, "cost_usd": _cost(calls),
                       "pixel_match": None, "warning": None,
                       "files": {"original": orig_name, "target": target_name, "output": None, "full": None}}
                if prep_error:
                    rec.update(status="failed", error=prep_error, provider_calls={"scene": 0, "upscale": 0}, cost_usd=None)
                    results.append(rec)
                    log(f"  {oid}: FAILED at cut-out ({prep_error})")
                    continue
                t1 = time.perf_counter()
                try:
                    _, _, final, score, warning = render(prepared, preset, canvas, 0.62, seed)
                    rec["seconds"] = round(prep_seconds + time.perf_counter() - t1, 2)
                    rec.update(pixel_match=round(score, 5), warning=warning)
                    if score < MIN_PIXEL_MATCH:
                        rec.update(status="failed", error=f"pixel check failed ({score:.4f})")
                    final.save(images / f"{oid}_full.png")
                    rec["files"].update(output=_review_copy(final, images / f"{oid}_output.jpg"),
                                        full=f"{oid}_full.png")
                except Exception as exc:  # noqa: BLE001
                    rec.update(status="failed", error=str(exc), seconds=round(time.perf_counter() - t1, 2))
                results.append(rec)
                log(f"  {oid}: {rec['status']} in {rec['seconds']}s")

    meta = {
        "name": name, "created_at": datetime.now(timezone.utc).isoformat(), "git_commit": _git_commit(),
        "dataset": str(dataset.root), "presets": presets, "aspect": aspect, "repeats": repeats,
        "providers": {"cutout": s.cutout_provider, "scene": s.scene_provider, "upscale": s.upscale_provider,
                      "flux_fill_model": s.flux_fill_model, "esrgan_model": s.esrgan_model,
                      "white_balance_strength": s.white_balance_strength},
        "external_processing": external,
        "items": [{"example_id": i.example_id, "category": i.category, "split": i.split, "tags": i.tags,
                   "must_keep": i.must_keep, "limitations": i.row.get("limitations", ""),
                   "metal": i.row.get("metal", ""), "stone": i.row.get("stone", ""),
                   "angles": 1 + len(i.extra_angles)} for i in dataset.items],
    }
    (run_dir / "run.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    (run_dir / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (run_dir / "reviews.json").write_text("{}", encoding="utf-8")
    return run_dir
