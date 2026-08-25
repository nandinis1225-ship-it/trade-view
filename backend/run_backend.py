"""Entry point for PyInstaller-packaged TRADEVERSE backend."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _configure_paths() -> None:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        os.environ.setdefault("PYTHONPATH", str(base))
    backend = Path(__file__).resolve().parent
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))


def main() -> None:
    _configure_paths()
    from app.paths import configure_packaged_runtime
    from app.core.config import get_settings

    configure_packaged_runtime()
    get_settings.cache_clear()

    import uvicorn

    settings = get_settings()
    host = os.environ.get("BACKEND_HOST", settings.backend_host)
    port = int(os.environ.get("BACKEND_PORT", settings.backend_port))

    if getattr(sys, "frozen", False) and host in ("0.0.0.0", "::"):
        raise SystemExit(
            "Packaged TRADEVERSE backend must bind to 127.0.0.1 only. "
            f"Refusing host={host!r}."
        )

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    main()
