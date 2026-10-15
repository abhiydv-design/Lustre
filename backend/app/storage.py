"""File storage. Local disk for the MVP; swap for S3 / Cloudflare R2 by
re-implementing these four functions with the same keys."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from .config import get_settings


def path_for(key: str) -> Path:
    root = get_settings().data_dir / "files"
    path = (root / key).resolve()
    if root.resolve() not in path.parents:
        raise ValueError("invalid storage key")
    return path


def save_bytes(key: str, data: bytes) -> str:
    path = path_for(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return key


def save_image(key: str, image: Image.Image, **kwargs) -> str:
    path = path_for(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, **kwargs)
    return key


def load_image(key: str) -> Image.Image:
    image = Image.open(path_for(key))
    image.load()
    return image
