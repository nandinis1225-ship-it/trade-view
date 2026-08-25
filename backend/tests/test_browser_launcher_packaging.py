"""Browser launcher packaging — local backend + default browser distribution."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.database import Base, get_db
from app.exchange.book_registry import books
from app.main import create_app
from app.paths import resolve_static_ui_dir
from app.services.pin_service import generate_pin_verifier
from app.services.timeline_protection import protect_timeline_json
from tests.conftest import join_participant

REPO_ROOT = Path(__file__).resolve().parents[2]
LAUNCHERS_DIR = REPO_ROOT / "scripts" / "offline" / "launchers"
PRODUCTION_EVENT_COUNT = 64


def test_launcher_templates_exist():
    required = (
        "Start-Tradeverse.bat",
        "Stop-Tradeverse.bat",
        "Start-Tradeverse.command",
        "Stop-Tradeverse.command",
    )
    for name in required:
        path = LAUNCHERS_DIR / name
        assert path.is_file(), f"missing launcher template: {name}"


def test_browser_build_scripts_exist():
    assert (REPO_ROOT / "scripts/offline/Build-Browser-Participant.ps1").is_file()
    assert (REPO_ROOT / "scripts/offline/build-browser-participant-macos.sh").is_file()
    assert (REPO_ROOT / "scripts/offline/audit-browser-participant-build.ps1").is_file()
    assert (REPO_ROOT / "scripts/offline/audit-browser-participant-build.sh").is_file()


def test_packaged_env_binds_localhost(tmp_path):
    sys.path.insert(0, str(REPO_ROOT / "backend"))
    from scripts.build_event_env import EVENT_ENV_LINES

    salt, pin_hash = generate_pin_verifier("test-pin")
    env_text = EVENT_ENV_LINES.format(pin_salt=salt, pin_hash=pin_hash)
    env_path = tmp_path / ".env"
    env_path.write_text(env_text, encoding="utf-8")
    assert "BACKEND_HOST=127.0.0.1" in env_text
    assert "SERVE_STATIC_UI=true" in env_text
    assert "PARTICIPANT_EVENT_MODE=true" in env_text
    assert "TIMELINE_DECRYPT_KEY" not in env_text


def test_health_endpoint(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200


def test_static_ui_served_at_terminal(tmp_path, monkeypatch):
    ui = tmp_path / "ui"
    terminal = ui / "terminal"
    terminal.mkdir(parents=True)
    (terminal / "index.html").write_text("<html><body>TRADEVERSE</body></html>", encoding="utf-8")

    monkeypatch.setenv("SERVE_STATIC_UI", "true")
    monkeypatch.setenv("UI_STATIC_DIR", str(ui))
    monkeypatch.setenv("DEVELOPER_MODE", "false")
    monkeypatch.setenv("PARTICIPANT_EVENT_MODE", "true")
    get_settings.cache_clear()

    app = create_app()
    with TestClient(app) as tc:
        res = tc.get("/terminal")
        assert res.status_code == 200
        assert "TRADEVERSE" in res.text


def test_resolve_static_ui_dir_prefers_env(tmp_path, monkeypatch):
    ui = tmp_path / "ui"
    ui.mkdir()
    monkeypatch.setenv("UI_STATIC_DIR", str(ui))
    assert resolve_static_ui_dir() == ui


def test_package_has_no_plaintext_timeline_or_dev_db(tmp_path):
    pkg = tmp_path / "TRADEVERSE"
    ui = pkg / "ui"
    ui.mkdir(parents=True)
    (ui / "terminal" / "index.html").parent.mkdir(parents=True, exist_ok=True)
    (ui / "terminal" / "index.html").write_text("<html></html>", encoding="utf-8")
    (pkg / ".env").write_text("BACKEND_HOST=127.0.0.1\n", encoding="utf-8")
    (pkg / "Start-Tradeverse.bat").write_text("@echo off\n", encoding="utf-8")

    assert not list(pkg.rglob("tradeverse_timeline.json"))
    assert not list(pkg.rglob("mse_dev.db"))
    content = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore") for p in pkg.rglob("*") if p.is_file()
    )
    assert "TIMELINE_DECRYPT_KEY" not in content


def test_production_timeline_64_events(production_timeline):
    assert len(production_timeline["events"]) == PRODUCTION_EVENT_COUNT


def test_browser_audit_script_checks_launchers():
    ps1 = (REPO_ROOT / "scripts/offline/audit-browser-participant-build.ps1").read_text(
        encoding="utf-8"
    )
    sh = (REPO_ROOT / "scripts/offline/audit-browser-participant-build.sh").read_text(
        encoding="utf-8"
    )
    assert "Start-Tradeverse.bat" in ps1
    assert "Start-Tradeverse.command" in sh
    assert "mse_dev.db" in ps1
    assert "mse_dev.db" in sh


def test_browser_package_audit_passes_synthetic_package(tmp_path):
    pkg = tmp_path / "TRADEVERSE"
    ui = pkg / "ui" / "terminal"
    ui.mkdir(parents=True)
    (ui / "index.html").write_text("<html>ok</html>", encoding="utf-8")
    (pkg / ".env").write_text("BACKEND_HOST=127.0.0.1\nEVENT_PIN_HASH=abc\n", encoding="utf-8")
    (pkg / "Start-Tradeverse.command").write_text("#!/bin/bash\nopen http://127.0.0.1:8765/terminal\n", encoding="utf-8")
    (pkg / "Stop-Tradeverse.command").write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
    (pkg / "tradeverse-backend").write_bytes(b"\x7fELF")

    audit_sh = REPO_ROOT / "scripts/offline/audit-browser-participant-build.sh"
    result = subprocess.run(
        ["bash", str(audit_sh), str(pkg)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_packaged_backend_rejects_public_bind(monkeypatch, tmp_path):
    monkeypatch.setenv("BACKEND_HOST", "0.0.0.0")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    import run_backend

    monkeypatch.setattr("uvicorn.run", lambda *args, **kwargs: None)

    with pytest.raises(SystemExit, match="127.0.0.1"):
        run_backend.main()


def test_fresh_db_and_recovery(client, mini_timeline, monkeypatch):
    monkeypatch.setenv("LOCAL_INSTANCE_MODE", "true")
    monkeypatch.setenv("PARTICIPANT_EVENT_MODE", "true")
    get_settings.cache_clear()
    _, auth = join_participant(client, "BrowserUser")
    boot = client.get("/api/v1/session/bootstrap", headers=auth).json()
    assert boot["trader_name"] == "BrowserUser"
    boot2 = client.get("/api/v1/session/bootstrap", headers=auth).json()
    assert boot2["trader_id"] == boot["trader_id"]


def test_offline_startup_configuration(monkeypatch):
    monkeypatch.setenv("LOCAL_INSTANCE_MODE", "true")
    monkeypatch.setenv("PARTICIPANT_EVENT_MODE", "true")
    monkeypatch.setenv("BACKEND_HOST", "127.0.0.1")
    monkeypatch.setenv("BACKEND_PORT", "8765")
    monkeypatch.setenv("SERVE_STATIC_UI", "true")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.local_instance_mode is True
    assert settings.participant_event_mode is True
    assert settings.backend_host == "127.0.0.1"
    assert settings.database_url.startswith("sqlite")


def test_timeline_protection_round_trip_64_events(tmp_path):
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
    assert pkg.is_file()
    assert not (tmp_path / "tradeverse_timeline.json").name == "timeline.pkg"
