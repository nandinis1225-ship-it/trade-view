#!/usr/bin/env python3
"""Ensure tradeverse_timeline.pkg exists with the production event count.

The repository ships tradeverse_timeline.enc (Fernet). This script validates an
existing protected package or creates one at build time without requiring a
local copy of tradeverse_timeline.json from another project.

Resolution order:
  1. Existing tradeverse_timeline.pkg with the expected event count
  2. tradeverse_timeline.json (organizer dev machine only, gitignored)
  3. tradeverse_timeline.enc + TIMELINE_DECRYPT_KEY environment variable
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.timeline_legacy_crypto import TIMELINE_ENC, decrypt_timeline_bytes
from app.services.timeline_protection import (
    TIMELINE_JSON,
    TIMELINE_PKG,
    load_protected_timeline,
    protect_timeline_bytes,
    protect_timeline_json,
)

MANIFEST_PATH = Path(__file__).resolve().parents[1] / "app" / "seed" / "timeline_manifest.json"
DEFAULT_EVENT_COUNT = 64


def _load_manifest() -> dict:
    if not MANIFEST_PATH.is_file():
        return {}
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _validate_event_count(data: dict, expected_events: int) -> None:
    events = data.get("events", [])
    if not isinstance(events, list):
        raise ValueError("timeline.events must be a list")
    if len(events) != expected_events:
        raise ValueError(f"expected {expected_events} timeline events, found {len(events)}")


def _validate_enc_artifact() -> None:
    if not TIMELINE_ENC.is_file():
        raise FileNotFoundError(f"committed production timeline missing: {TIMELINE_ENC}")
    manifest = _load_manifest()
    expected_sha = manifest.get("enc_sha256")
    if expected_sha:
        actual_sha = hashlib.sha256(TIMELINE_ENC.read_bytes()).hexdigest()
        if actual_sha != expected_sha:
            raise ValueError(
                "tradeverse_timeline.enc checksum mismatch — "
                "expected production artifact was modified"
            )


def validate_protected_package(
    pkg_path: Path | None = None,
    *,
    expected_events: int = DEFAULT_EVENT_COUNT,
) -> dict:
    pkg = pkg_path or TIMELINE_PKG
    if not pkg.is_file():
        raise FileNotFoundError(f"protected timeline package not found: {pkg}")
    data = load_protected_timeline(pkg)
    _validate_event_count(data, expected_events)
    return data


def ensure_production_timeline_pkg(
    *,
    expected_events: int = DEFAULT_EVENT_COUNT,
    force: bool = False,
) -> Path:
    """Return path to a valid protected production timeline package."""
    _validate_enc_artifact()

    if TIMELINE_PKG.is_file() and not force:
        validate_protected_package(TIMELINE_PKG, expected_events=expected_events)
        return TIMELINE_PKG

    if TIMELINE_JSON.is_file():
        protect_timeline_json(TIMELINE_JSON, dest=TIMELINE_PKG, expected_events=expected_events)
        validate_protected_package(TIMELINE_PKG, expected_events=expected_events)
        return TIMELINE_PKG

    key = os.environ.get("TIMELINE_DECRYPT_KEY", "").strip()
    if key:
        data = decrypt_timeline_bytes(key, TIMELINE_ENC.read_bytes())
        _validate_event_count(data, expected_events)
        plaintext = json.dumps(data, ensure_ascii=False).encode("utf-8")
        TIMELINE_PKG.write_bytes(protect_timeline_bytes(plaintext))
        validate_protected_package(TIMELINE_PKG, expected_events=expected_events)
        return TIMELINE_PKG

    raise RuntimeError(
        "Production timeline package is missing. A clean checkout includes "
        "backend/app/seed/tradeverse_timeline.enc. Set TIMELINE_DECRYPT_KEY in "
        "your organizer environment (or pass it for this build step) so the "
        "build can create tradeverse_timeline.pkg, or place a valid "
        "tradeverse_timeline.pkg in backend/app/seed/."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Ensure protected production timeline package")
    parser.add_argument("--events", type=int, default=DEFAULT_EVENT_COUNT)
    parser.add_argument("--force", action="store_true", help="Regenerate package even if one exists")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate existing package without creating one",
    )
    args = parser.parse_args()

    try:
        if args.validate_only:
            out = validate_protected_package(expected_events=args.events)
        else:
            out_path = ensure_production_timeline_pkg(expected_events=args.events, force=args.force)
            out = validate_protected_package(out_path, expected_events=args.events)
            print(f"Protected timeline ready: {out_path}")
            print(f"Validated {len(out['events'])} production events")
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
