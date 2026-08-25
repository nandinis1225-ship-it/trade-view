"""Build Tradeverse-Participant.zip for sharing with club members."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_BUILD_SCRIPT = _PROJECT_ROOT / "scripts" / "offline" / "build-share-package.ps1"
_ZIP_PATH = _PROJECT_ROOT / "Tradeverse-Participant.zip"


class ParticipantPackageError(Exception):
    """Failed to build participant zip."""


def build_participant_zip() -> dict:
    if not _BUILD_SCRIPT.is_file():
        raise ParticipantPackageError(f"build script not found: {_BUILD_SCRIPT}")

    from app.core.config import get_settings

    settings = get_settings()
    event_pin = (settings.event_pin or "").strip()
    if not event_pin:
        raise ParticipantPackageError("EVENT_PIN is not configured")

    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(_BUILD_SCRIPT),
                "-EventPin",
                event_pin,
            ],
            cwd=str(_PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ParticipantPackageError("build timed out after 10 minutes") from exc
    except OSError as exc:
        raise ParticipantPackageError(f"could not run build script: {exc}") from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "build failed").strip()[:500]
        logger.error("participant zip build failed: %s", detail)
        raise ParticipantPackageError(detail)

    if not _ZIP_PATH.is_file():
        raise ParticipantPackageError("zip was not created")

    size = _ZIP_PATH.stat().st_size
    return {
        "ok": True,
        "action": "build_participant_zip",
        "zip_path": str(_ZIP_PATH),
        "zip_name": _ZIP_PATH.name,
        "zip_size_bytes": size,
        "zip_size_mb": f"{size / (1024 * 1024):.2f}",
    }
