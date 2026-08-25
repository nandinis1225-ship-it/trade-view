"""Developer-mode access guards (localhost-only internal tooling)."""

from __future__ import annotations

from fastapi import HTTPException, Request

from app.core.config import get_settings


def require_developer_mode() -> None:
    if not get_settings().developer_mode:
        raise HTTPException(status_code=404, detail="not found")


def require_local_developer(request: Request) -> None:
    require_developer_mode()
    host = request.client.host if request.client else ""
    if host not in ("127.0.0.1", "::1", "localhost", "testclient"):
        raise HTTPException(status_code=403, detail="developer actions only from localhost")


def require_ipo_admin() -> None:
    """IPO admin lifecycle — only when developer mode is enabled."""
    require_developer_mode()
