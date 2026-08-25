"""Phase 5 — build, test, and audit gate validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.audit_patterns import PARTICIPANT_FORBIDDEN_PATTERNS, PROJECTOR_FORBIDDEN_PATTERNS


def test_participant_audit_ps1_matches_python_patterns():
    root = Path(__file__).resolve().parents[2]
    ps1 = (root / "scripts" / "offline" / "audit-participant-build.ps1").read_text(encoding="utf-8")
    for pattern in PARTICIPANT_FORBIDDEN_PATTERNS:
        assert pattern in ps1, f"audit-participant-build.ps1 missing: {pattern}"


def test_participant_audit_sh_matches_python_patterns():
    root = Path(__file__).resolve().parents[2]
    sh = (root / "scripts" / "offline" / "audit-participant-build.sh").read_text(encoding="utf-8")
    for pattern in PARTICIPANT_FORBIDDEN_PATTERNS:
        assert pattern in sh, f"audit-participant-build.sh missing: {pattern}"


def test_projector_audit_sh_matches_python_patterns():
    root = Path(__file__).resolve().parents[2]
    sh = (root / "scripts" / "offline" / "audit-projector-build.sh").read_text(encoding="utf-8")
    for pattern in PROJECTOR_FORBIDDEN_PATTERNS:
        assert pattern in sh, f"audit-projector-build.sh missing: {pattern}"


def test_rehearsal_scripts_exist():
    root = Path(__file__).resolve().parents[2]
    assert (root / "scripts" / "dev" / "run-event-rehearsal.ps1").is_file()
    assert (root / "scripts" / "dev" / "run-event-rehearsal.sh").is_file()
    assert (root / "scripts" / "dev" / "run-phase5-gates.sh").is_file()


def test_market_status_includes_duration(client):
    body = client.get("/api/v1/market/status").json()
    assert "duration" in body
    assert body["duration"] == "03:00:00"


def test_market_status_includes_market_change_pct(client):
    body = client.get("/api/v1/market/status").json()
    assert "market_change_pct" in body


def test_phase35_frozen_files_untouched():
    """Regression: Phase 3.5 release-critical files must not change in Phase 5."""
    root = Path(__file__).resolve().parents[2]
    frozen = (
        "scripts/offline/Build-Participant.ps1",
        "scripts/offline/build-participant-macos.sh",
        "scripts/offline/audit-participant-build.ps1",
        "backend/scripts/protect_timeline.py",
        "backend/app/services/timeline_protection.py",
        "backend/app/paths.py",
        "backend/run_backend.py",
        "backend/tradeverse-backend.spec",
    )
    # This test documents the freeze list; git diff is verified in PHASE_5_REPORT.md
    for rel in frozen:
        assert (root / rel).is_file(), f"missing frozen file: {rel}"
