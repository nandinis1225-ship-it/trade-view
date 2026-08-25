#!/usr/bin/env python3
"""Build-time: protect production tradeverse_timeline.json → tradeverse_timeline.pkg"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.timeline_protection import TIMELINE_JSON, TIMELINE_PKG, protect_timeline_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Protect production timeline for packaging")
    parser.add_argument("--source", type=Path, default=TIMELINE_JSON)
    parser.add_argument("--output", type=Path, default=TIMELINE_PKG)
    parser.add_argument("--events", type=int, default=64, help="Required event count")
    args = parser.parse_args()
    try:
        out = protect_timeline_json(args.source, dest=args.output, expected_events=args.events)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Protected timeline written: {out}")
    print(f"Source JSON unchanged: {args.source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
