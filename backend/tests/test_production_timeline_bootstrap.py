"""Production timeline bootstrap — clean checkout and packaging prerequisites."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from app.services.timeline_protection import protect_timeline_json

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_DIR = REPO_ROOT / "backend" / "app" / "seed"
ENC_PATH = SEED_DIR / "tradeverse_timeline.enc"
MANIFEST_PATH = SEED_DIR / "timeline_manifest.json"
ENSURE_SCRIPT = REPO_ROOT / "backend" / "scripts" / "ensure_production_timeline_pkg.py"
BUILD_PS1 = REPO_ROOT / "scripts" / "offline" / "Build-Browser-Participant.ps1"
PRODUCTION_EVENT_COUNT = 64


def test_repo_contains_committed_production_timeline_enc():
    assert ENC_PATH.is_file(), "tradeverse_timeline.enc must be committed in the repository"
    assert ENC_PATH.stat().st_size > 1000


def test_timeline_manifest_matches_committed_enc():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["production_event_count"] == PRODUCTION_EVENT_COUNT
    actual_sha = hashlib.sha256(ENC_PATH.read_bytes()).hexdigest()
    assert manifest["enc_sha256"] == actual_sha
    assert manifest["enc_bytes"] == ENC_PATH.stat().st_size


def test_clean_checkout_has_participant_build_prerequisites():
    required = (
        ENSURE_SCRIPT,
        BUILD_PS1,
        REPO_ROOT / "backend" / "app" / "seed" / "tradeverse_universe.json",
        REPO_ROOT / "backend" / "tradeverse-backend.spec",
        REPO_ROOT / "scripts" / "offline" / "launchers" / "Start-Tradeverse.bat",
    )
    for path in required:
        assert path.is_file(), f"missing build prerequisite: {path}"


def test_browser_build_script_has_no_external_timeline_prerequisites():
    raw = BUILD_PS1.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    text = raw.decode("utf-8")
    assert "tradeverse_timeline.json" not in text
    assert "mock market simulation" not in text.lower()
    assert "ensure_production_timeline_pkg.py" in text
    assert '$env:EVENT_PIN' in text or '$EventPin = $env:EVENT_PIN' in text


def test_ensure_script_validates_event_count(tmp_path):
    sys.path.insert(0, str(REPO_ROOT / "backend"))
    from scripts.ensure_production_timeline_pkg import validate_protected_package

    src = tmp_path / "timeline.json"
    events = []
    for i in range(1, PRODUCTION_EVENT_COUNT + 1):
        events.append(
            {
                "checkpoint_id": i,
                "time": "03:00:00" if i == PRODUCTION_EVENT_COUNT else f"00:{i:02d}",
                "type": "SIMULATION_END" if i == PRODUCTION_EVENT_COUNT else "NEWS",
                "phase": "PHASE 1",
                "headline": f"Event {i}",
                "description": "",
                "payload": {"sector_impacts": {"it": 1.0}} if i < PRODUCTION_EVENT_COUNT else {},
            }
        )
    src.write_text(json.dumps({"events": events}), encoding="utf-8")
    pkg = tmp_path / "timeline.pkg"
    protect_timeline_json(src, dest=pkg, expected_events=PRODUCTION_EVENT_COUNT)
    data = validate_protected_package(pkg, expected_events=PRODUCTION_EVENT_COUNT)
    assert len(data["events"]) == PRODUCTION_EVENT_COUNT


def test_ensure_script_rejects_wrong_event_count(tmp_path, monkeypatch):
    sys.path.insert(0, str(REPO_ROOT / "backend"))
    from scripts.ensure_production_timeline_pkg import validate_protected_package

    src = tmp_path / "timeline.json"
    src.write_text(json.dumps({"events": [{"checkpoint_id": 1}]}), encoding="utf-8")
    pkg = tmp_path / "timeline.pkg"
    protect_timeline_json(src, dest=pkg, expected_events=1)
    with pytest.raises(ValueError, match="expected 64"):
        validate_protected_package(pkg, expected_events=PRODUCTION_EVENT_COUNT)


@pytest.mark.skipif(
    not os.environ.get("TIMELINE_DECRYPT_KEY"),
    reason="TIMELINE_DECRYPT_KEY required to bootstrap production .pkg from .enc",
)
def test_ensure_script_bootstraps_pkg_from_enc(tmp_path, monkeypatch):
    sys.path.insert(0, str(REPO_ROOT / "backend"))
    import scripts.ensure_production_timeline_pkg as ensure_mod

    pkg_path = tmp_path / "tradeverse_timeline.pkg"
    monkeypatch.setattr(ensure_mod, "TIMELINE_PKG", pkg_path)
    monkeypatch.setattr(ensure_mod, "TIMELINE_JSON", tmp_path / "missing.json")

    out = ensure_mod.ensure_production_timeline_pkg(expected_events=PRODUCTION_EVENT_COUNT)
    assert out == pkg_path
    data = ensure_mod.validate_protected_package(out, expected_events=PRODUCTION_EVENT_COUNT)
    assert len(data["events"]) == PRODUCTION_EVENT_COUNT


def test_ensure_script_cli_validate_only_fails_without_pkg():
    result = subprocess.run(
        [sys.executable, str(ENSURE_SCRIPT), "--validate-only"],
        cwd=REPO_ROOT / "backend",
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0


def test_powershell_build_scripts_parse_cleanly():
  ps1_files = [
      REPO_ROOT / "scripts/offline/Build-Browser-Participant.ps1",
      REPO_ROOT / "scripts/offline/audit-browser-participant-build.ps1",
      REPO_ROOT / "scripts/dev/run-event-rehearsal.ps1",
  ]
  pwsh = shutil.which("pwsh") or shutil.which("powershell")
  if not pwsh:
      pytest.skip("PowerShell not installed")
  for path in ps1_files:
      result = subprocess.run(
          [
              pwsh,
              "-NoProfile",
              "-Command",
              f"$e=$null; [void][System.Management.Automation.Language.Parser]::ParseFile('{path}', [ref]$null, [ref]$e); if ($e) {{ $e | ForEach-Object {{ Write-Output $_ }}; exit 1 }}",
          ],
          capture_output=True,
          text=True,
          check=False,
      )
      assert result.returncode == 0, f"{path.name} parse failed: {result.stdout}{result.stderr}"
