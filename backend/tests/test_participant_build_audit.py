"""Participant static build must not ship developer routes or organizer strings."""

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
    "sector_impacts",
    "effective_impact",
    "stop_loss",
    "take_profit",
    "tradeverse_timeline.json",
)
ALLOWED_TERMINAL_TOKENS = frozenset({"MARKET_PULSE"})


def _scan_participant_out(out: Path) -> list[str]:
    failures: list[str] = []
    for forbidden in FORBIDDEN_DIRS:
        if (out / forbidden).exists():
            failures.append(f"participant build must not include out/{forbidden}")
    for path in out.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(out))
        if rel.startswith("_next/static/chunks/framework"):
            continue
        if "/framework-" in rel:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in content:
                failures.append(f"{rel}: contains '{pattern}'")
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
    assert not failures, "\n".join(failures[:25])


def test_participant_terminal_bundle_has_no_admin_strings():
    root = Path(__file__).resolve().parents[2]
    terminal_chunks = list((root / "frontend" / "out").glob("_next/static/chunks/app/terminal/*.js"))
    if not terminal_chunks:
        return
    for chunk in terminal_chunks:
        text = chunk.read_text(encoding="utf-8", errors="ignore")
        for pattern in FORBIDDEN_PATTERNS:
            assert pattern not in text, f"{chunk.name} contains {pattern}"
        for token in ("AI_TICK", "fair_value", "sector_impact"):
            if token in text and token not in ALLOWED_TERMINAL_TOKENS:
                # MARKET_PULSE handler string is acceptable; others are not
                if token != "MARKET_PULSE":
                    assert False, f"{chunk.name} contains {token}"
