"""Filesystem paths for packaged and development TRADEVERSE."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def packaged_root() -> Path | None:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return None


def resolve_static_ui_dir() -> Path | None:
    env = os.environ.get("UI_STATIC_DIR")
    if env:
        path = Path(env)
        if path.is_dir():
            return path
    root = packaged_root()
    if root is not None:
        ui = root / "ui"
        if ui.is_dir():
            return ui
    dev = Path(__file__).resolve().parents[2] / "frontend" / "out"
    if dev.is_dir():
        return dev
    return None


def configure_packaged_runtime() -> Path | None:
    """Apply defaults when running as a PyInstaller sidecar."""
    root = packaged_root()
    if root is None:
        return None
    os.chdir(root)
    os.environ.setdefault("LOCAL_INSTANCE_MODE", "true")
    os.environ.setdefault("AUTO_INIT_DB", "true")
    os.environ.setdefault("SERVE_STATIC_UI", "true")
    os.environ.setdefault("BACKEND_HOST", "127.0.0.1")
    os.environ.setdefault("BACKEND_PORT", "8765")
    os.environ.setdefault("ENVIRONMENT", "production")
    os.environ.setdefault("DEBUG", "false")
    ui = root / "ui"
    if ui.is_dir():
        os.environ.setdefault("UI_STATIC_DIR", str(ui))
    return root
