"""Strip schedule spoilers from tradeverse_universe.json for participant packages."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_SOURCE = Path(__file__).resolve().parents[1] / "app" / "seed" / "tradeverse_universe.json"


def sanitize_universe(data: dict[str, Any]) -> dict[str, Any]:
    """Return participant-safe universe — no phase schedule or future event spoilers."""
    out = dict(data)
    out.pop("phases", None)
    out.pop("dissolution_events", None)

    ipo_defs = []
    for row in data.get("ipo_definitions", []):
        cleaned = dict(row)
        for key in ("open_time", "allotment_time", "listing_time"):
            cleaned.pop(key, None)
        ipo_defs.append(cleaned)
    out["ipo_definitions"] = ipo_defs
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Sanitize universe JSON for participant zip")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    with args.source.open(encoding="utf-8") as f:
        data = json.load(f)

    sanitized = sanitize_universe(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(sanitized, f, indent=2)
        f.write("\n")

    print(f"Wrote participant universe to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
