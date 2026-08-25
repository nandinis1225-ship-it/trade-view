"""Participant static build must not ship developer routes."""

from __future__ import annotations

from pathlib import Path


def test_participant_out_prunes_developer_routes():
    root = Path(__file__).resolve().parents[2]
    out = root / "frontend" / "out"
    if not out.is_dir():
        return
    for forbidden in ("admin", "market-screen", "developer"):
        assert not (out / forbidden).exists(), f"participant build must not include out/{forbidden}"
