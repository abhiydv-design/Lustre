"""Jewellery Image Studio backend. Run:  uvicorn app.main:app --reload"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import init_db
from .pipeline.run import recover_interrupted
from .routes import admin, auth, generations, payments, products


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=logging.INFO)
    init_db(settings.database_url)
    recovered = recover_interrupted()
    if recovered:
        logging.getLogger("studio").warning("refunded %d interrupted generations", recovered)
    if not settings.dev_mode and settings.secret_key == "dev-only-change-me":
        raise RuntimeError("Set SECRET_KEY before running with DEV_MODE=0")
    app = FastAPI(title=f"{settings.brand_name} API", version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"],
                       allow_headers=["*"], expose_headers=["X-Pixel-Match", "X-Quality-Warning"])
    app.include_router(auth.router)
    app.include_router(products.router)
    app.include_router(generations.router)
    app.include_router(payments.router)
    app.include_router(admin.router)

    @app.get("/health")
    def health():
        return {"ok": True, "scene": settings.scene_provider, "upscale": settings.upscale_provider,
                "cutout": settings.cutout_provider}

    return app


app = create_app()
