"""Backward-compatible shim — use timeline_protection (no Fernet / decrypt key)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.timeline_protection import (
    TIMELINE_JSON,
    TIMELINE_PKG,
    load_protected_timeline,
    load_timeline_data,
    protect_timeline_json,
)

SEED_DIR = Path(__file__).resolve().parents[1] / "seed"
TIMELINE_ENC = TIMELINE_PKG  # legacy alias
TIMELINE_BAKED = SEED_DIR / "tradeverse_timeline.baked.json"


def bake_timeline_for_participant(_key: str = "", *, dest: Path | None = None) -> Path:
    """Deprecated — participant builds embed tradeverse_timeline.pkg in the backend binary."""
    raise RuntimeError(
        "bake_timeline_for_participant is deprecated; run scripts/protect_timeline.py instead"
    )


__all__ = [
    "TIMELINE_JSON",
    "TIMELINE_PKG",
    "TIMELINE_ENC",
    "TIMELINE_BAKED",
    "load_timeline_data",
    "load_protected_timeline",
    "protect_timeline_json",
    "bake_timeline_for_participant",
]
