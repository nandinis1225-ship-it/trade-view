#!/usr/bin/env python3
"""Deprecated — use scripts/protect_timeline.py (no TIMELINE_DECRYPT_KEY)."""

from __future__ import annotations

import sys
from pathlib import Path

print(
    "encrypt_timeline.py is deprecated. Use: python scripts/protect_timeline.py",
    file=sys.stderr,
)
sys.exit(1)
