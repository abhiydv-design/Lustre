"""Marketplace export presets (spec §13.2).

A preset is only offered to users once `verified_on` and `source` are filled in from the
marketplace's current seller documentation. Requirements change, so re-check them regularly
and update `verified_on`. Nothing here is verified yet: this file intentionally ships empty.

Example entry (fill every field from the official seller guide before adding):

    MarketplacePreset(
        id="example_main",
        marketplace="Example Marketplace",
        slot="Main listing image",
        width=0, height=0,                 # required/recommended pixel size
        formats=("jpg",),                  # accepted file types
        max_file_mb=None,                  # size limit, if any
        background="pure white (255,255,255)",
        style="white",                     # which preset satisfies the background rule
        fill=0.85,                         # share of the shorter side the piece should occupy
        rules="Product fully visible, no text, no watermark, no props",
        source="https://... (official seller help page)",
        verified_on="YYYY-MM-DD",
    )
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MarketplacePreset:
    id: str
    marketplace: str
    slot: str
    width: int
    height: int
    formats: tuple[str, ...]
    max_file_mb: float | None
    background: str
    style: str
    fill: float
    rules: str
    source: str
    verified_on: str | None


PRESETS: list[MarketplacePreset] = []


def verified() -> dict[str, MarketplacePreset]:
    return {p.id: p for p in PRESETS if p.verified_on and p.source and p.width and p.height}
