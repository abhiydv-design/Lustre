"""Lustre backend. Run:  uvicorn app.main:app --reload"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import init_db
from .routes import account, payments, studio


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=logging.INFO)
    init_db(settings.database_url)
    app = FastAPI(title=f"{settings.brand_name} API", version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"],
                       allow_headers=["*"], expose_headers=["X-Fidelity", "X-Quality-Warning"])
    app.include_router(account.router)
    app.include_router(studio.router)
    app.include_router(payments.router)

    @app.get("/health")
    def health():
        return {"ok": True, "scene": settings.scene_provider, "upscale": settings.upscale_provider,
                "cutout": settings.cutout_provider}

    return app


app = create_app()
