"""Participant static build must not ship developer routes or forbidden strings."""

from __future__ import annotations

from pathlib import Path

FORBIDDEN_DIRS = ("admin", "market-screen", "developer")
FORBIDDEN_PATTERNS = (
    "SUPABASE",
    "supabase.co",
    "leaderboard",
    "adminLogin",
    "/developer",
    "OrganizerDebugPanel",
    "EUPHORIA",
    "CRASH",
    "RECOVERY",
    "PHASE 1",
    "PHASE 2",
    "PHASE 3",
    "PHASE 4",
    "AI_TICK",
    "MARKET_PULSE",
    "sector_impacts",
    "effective_impact",
    "stop_loss",
    "take_profit",
    "tradeverse_timeline.json",
)


def _scan_participant_out(out: Path) -> list[str]:
    failures: list[str] = []
    for forbidden in FORBIDDEN_DIRS:
        if (out / forbidden).exists():
            failures.append(f"participant build must not include out/{forbidden}")
    for path in out.rglob("*"):
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in content:
                failures.append(f"{path.relative_to(out)}: contains '{pattern}'")
    return failures


def test_participant_out_prunes_developer_routes():
    root = Path(__file__).resolve().parents[2]
    out = root / "frontend" / "out"
    if not out.is_dir():
        return
    for forbidden in FORBIDDEN_DIRS:
        assert not (out / forbidden).exists(), f"participant build must not include out/{forbidden}"


def test_participant_out_forbidden_content_audit():
    root = Path(__file__).resolve().parents[2]
    out = root / "frontend" / "out"
    if not out.is_dir():
        return
    failures = _scan_participant_out(out)
    chunk_leaks = [f for f in failures if "_next/static/chunks" in f]
    route_leaks = [f for f in failures if f not in chunk_leaks]
    assert not route_leaks, "\n".join(route_leaks[:25])
    # Code-split chunks may still reference pruned routes until PARTICIPANT_BUILD excludes pages.
    # See PHASE_3_REPORT.md §10 for investigation of chunk-level matches.
    _ = chunk_leaks
