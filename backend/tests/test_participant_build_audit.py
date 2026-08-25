"""Participant static build must not ship developer routes or organizer strings."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.audit_patterns import PARTICIPANT_FORBIDDEN_DIRS, PARTICIPANT_FORBIDDEN_PATTERNS

ALLOWED_TERMINAL_TOKENS = frozenset({"MARKET_PULSE"})

# Terminal WS handler may reference MARKET_PULSE (server suppresses in event mode).
PARTICIPANT_SCAN_PATTERNS = tuple(
    p for p in PARTICIPANT_FORBIDDEN_PATTERNS if p not in ALLOWED_TERMINAL_TOKENS
)


def _scan_participant_out(out: Path) -> list[str]:
    failures: list[str] = []
    for forbidden in PARTICIPANT_FORBIDDEN_DIRS:
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
        for pattern in PARTICIPANT_SCAN_PATTERNS:
            if pattern in content:
                failures.append(f"{rel}: contains '{pattern}'")
    return failures


def test_participant_out_prunes_developer_routes():
    root = Path(__file__).resolve().parents[2]
    out = root / "frontend" / "out"
    if not out.is_dir():
        return
    if not (out / "terminal").is_dir():
        pytest.skip("participant build not present — run npm run build:participant first")
    if (out / "projector").is_dir():
        pytest.skip("mixed out/ tree — rebuild with npm run build:participant only")
    for forbidden in PARTICIPANT_FORBIDDEN_DIRS:
        assert not (out / forbidden).exists(), f"participant build must not include out/{forbidden}"


def test_participant_out_forbidden_content_audit():
    root = Path(__file__).resolve().parents[2]
    out = root / "frontend" / "out"
    if not out.is_dir():
        return
    if not (out / "terminal").is_dir():
        pytest.skip("participant build not present — run npm run build:participant first")
    if (out / "projector").is_dir():
        pytest.skip("mixed out/ tree — rebuild with npm run build:participant only")
    failures = _scan_participant_out(out)
    assert not failures, "\n".join(failures[:25])


def test_participant_terminal_bundle_has_no_admin_strings():
    root = Path(__file__).resolve().parents[2]
    terminal_chunks = list((root / "frontend" / "out").glob("_next/static/chunks/app/terminal/*.js"))
    if not terminal_chunks:
        return
    for chunk in terminal_chunks:
        text = chunk.read_text(encoding="utf-8", errors="ignore")
        for pattern in PARTICIPANT_SCAN_PATTERNS:
            assert pattern not in text, f"{chunk.name} contains {pattern}"
        for token in ("AI_TICK", "fair_value", "sector_impact"):
            if token in text and token not in ALLOWED_TERMINAL_TOKENS:
                assert False, f"{chunk.name} contains {token}"


def test_audit_script_pattern_parity_with_python_gate():
    """PowerShell audit script (frozen) must match Python gate patterns."""
    root = Path(__file__).resolve().parents[2]
    ps1 = root / "scripts" / "offline" / "audit-participant-build.ps1"
    text = ps1.read_text(encoding="utf-8")
    for pattern in PARTICIPANT_FORBIDDEN_PATTERNS:
        assert pattern in text, f"audit-participant-build.ps1 missing pattern: {pattern}"
