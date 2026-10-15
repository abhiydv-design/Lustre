"""Settings, read from environment variables (see .env.example)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def _int(name: str, default: int) -> int:
    return int(_env(name, str(default)))


def _bool(name: str, default: bool) -> bool:
    return _env(name, "1" if default else "0").lower() in ("1", "true", "yes", "on")


def _price(name: str) -> int | None:
    value = _env(name)
    return int(value) if value is not None else None


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    database_url: str
    dev_mode: bool
    secret_key: str
    brand_name: str
    cors_origins: list[str]

    cutout_provider: str
    rembg_model: str
    scene_provider: str
    upscale_provider: str
    flux_fill_model: str
    esrgan_model: str
    preview_long_side: int
    white_balance_strength: float

    trial_credits: int
    initial_generation_cost: int
    additional_generation_cost: int
    quality_refund_auto_limit: int  # automatic detail-error refunds per user per 30 days
    max_upload_mb: int
    max_photos_per_product: int

    sms_provider: str
    admin_tokens: dict[str, str]      # token -> admin name
    cost_per_scene_inr: float
    cost_per_upscale_inr: float

    pack_prices_inr: dict[str, int | None]
    razorpay_key_id: str | None
    razorpay_key_secret: str | None
    razorpay_webhook_secret: str | None


@lru_cache
def get_settings() -> Settings:
    data_dir = Path(_env("DATA_DIR", "./data")).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    return Settings(
        data_dir=data_dir,
        database_url=_env("DATABASE_URL", f"sqlite:///{data_dir / 'studio.db'}"),
        dev_mode=_bool("DEV_MODE", True),
        secret_key=_env("SECRET_KEY", "dev-only-change-me"),
        brand_name=_env("BRAND_NAME", "Jewellery Image Studio"),
        cors_origins=[o.strip() for o in _env("CORS_ORIGINS", "*").split(",")],
        cutout_provider=_env("CUTOUT_PROVIDER", "threshold"),
        rembg_model=_env("REMBG_MODEL", "birefnet-general"),
        scene_provider=_env("SCENE_PROVIDER", "mock"),
        upscale_provider=_env("UPSCALE_PROVIDER", "lanczos"),
        flux_fill_model=_env("FLUX_FILL_MODEL", "black-forest-labs/flux-fill-pro"),
        esrgan_model=_env("ESRGAN_MODEL", "nightmareai/real-esrgan"),
        preview_long_side=_int("PREVIEW_LONG_SIDE", 1024),
        white_balance_strength=float(_env("WHITE_BALANCE_STRENGTH", "0.5")),
        trial_credits=_int("TRIAL_CREDITS", 3),
        initial_generation_cost=_int("INITIAL_GENERATION_COST", 1),
        additional_generation_cost=_int("ADDITIONAL_GENERATION_COST", 1),
        quality_refund_auto_limit=_int("QUALITY_REFUND_AUTO_LIMIT", 5),
        max_upload_mb=_int("MAX_UPLOAD_MB", 25),
        max_photos_per_product=_int("MAX_PHOTOS_PER_PRODUCT", 8),
        sms_provider=_env("SMS_PROVIDER", "console"),
        admin_tokens={tok: name for name, _, tok in
                      (pair.strip().partition(":") for pair in _env("ADMIN_TOKENS", "").split(",") if pair.strip())
                      if tok},
        cost_per_scene_inr=float(_env("COST_PER_SCENE_INR", "0")),
        cost_per_upscale_inr=float(_env("COST_PER_UPSCALE_INR", "0")),
        pack_prices_inr={
            "starter": _price("PACK_STARTER_PRICE_INR"),
            "shop": _price("PACK_SHOP_PRICE_INR"),
            "studio": _price("PACK_STUDIO_PRICE_INR"),
        },
        razorpay_key_id=_env("RAZORPAY_KEY_ID"),
        razorpay_key_secret=_env("RAZORPAY_KEY_SECRET"),
        razorpay_webhook_secret=_env("RAZORPAY_WEBHOOK_SECRET"),
    )
