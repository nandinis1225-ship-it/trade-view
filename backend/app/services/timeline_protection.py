"""Build-time timeline protection — obfuscated embedded resource, no participant key.

Not intended to resist determined reverse engineering; prevents casual inspection
of future event data in participant packages.
"""

from __future__ import annotations

import json
import zlib
from pathlib import Path
from typing import Any

SEED_DIR = Path(__file__).resolve().parents[1] / "seed"
TIMELINE_JSON = SEED_DIR / "tradeverse_timeline.json"
TIMELINE_PKG = SEED_DIR / "tradeverse_timeline.pkg"

# Embedded build constant — compiled into the backend binary / participant package.
_EMBED_KEY = b"TRADEVERSE-TIMELINE-v1-64evt"


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    if not key:
        return data
    out = bytearray(len(data))
    for i, b in enumerate(data):
        out[i] = b ^ key[i % len(key)]
    return bytes(out)


def protect_timeline_bytes(plaintext: bytes) -> bytes:
    compressed = zlib.compress(plaintext, level=9)
    return _xor_bytes(compressed, _EMBED_KEY)


def unprotect_timeline_bytes(blob: bytes) -> bytes:
    deobfuscated = _xor_bytes(blob, _EMBED_KEY)
    return zlib.decompress(deobfuscated)


def protect_timeline_json(
    source: Path | None = None,
    *,
    dest: Path | None = None,
    expected_events: int = 64,
) -> Path:
    """Read production JSON, verify event count, write protected package."""
    src = source or TIMELINE_JSON
    out = dest or TIMELINE_PKG
    if not src.is_file():
        raise FileNotFoundError(f"production timeline JSON not found: {src}")
    raw = src.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("timeline must be a JSON object")
    events = data.get("events", [])
    if not isinstance(events, list):
        raise ValueError("timeline.events must be a list")
    if len(events) != expected_events:
        raise ValueError(f"expected {expected_events} timeline events, found {len(events)}")
    out.write_bytes(protect_timeline_bytes(raw))
    return out


def load_protected_timeline(path: Path | None = None) -> dict[str, Any]:
    pkg = path or TIMELINE_PKG
    if not pkg.is_file():
        raise FileNotFoundError(f"protected timeline package not found: {pkg}")
    plaintext = unprotect_timeline_bytes(pkg.read_bytes())
    data = json.loads(plaintext.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("protected timeline is not a JSON object")
    return data


def load_timeline_data() -> dict[str, Any]:
    """Load timeline for runtime — protected package preferred, plaintext JSON for dev only."""
    if TIMELINE_PKG.is_file():
        return load_protected_timeline(TIMELINE_PKG)
    if TIMELINE_JSON.is_file():
        with TIMELINE_JSON.open(encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("timeline JSON must be an object")
        return data
    raise ValueError(
        "Timeline not available — build tradeverse_timeline.pkg from production JSON"
    )
