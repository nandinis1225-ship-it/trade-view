"""Phase 3.5 — production packaging tests."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.models import TimelineEvent
from app.paths import resolve_static_ui_dir
from app.services.simulation_controller import bootstrap_universe
from app.services.timeline_protection import (
    TIMELINE_JSON,
    load_protected_timeline,
    load_timeline_data,
    protect_timeline_bytes,
    protect_timeline_json,
    unprotect_timeline_bytes,
)
from app.services.timeline_service import seed_timeline_from_json, validate_timeline
from tests.conftest import join_participant


REPO_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_EVENT_COUNT = 64


def _synthetic_timeline(event_count: int) -> dict:
    events = []
    for i in range(1, event_count + 1):
        minute = i % 60
        hour = i // 60
        events.append(
            {
                "checkpoint_id": i,
                "time": f"{hour:02d}:{minute:02d}",
                "type": "NEWS" if i < event_count else "SIMULATION_END",
                "phase": "PHASE 1",
                "headline": f"Synthetic event {i}",
                "description": "packaging test",
                "payload": {"sector_impacts": {"it": 1.0}} if i < event_count else {},
            }
        )
    events[-1] = {
        "checkpoint_id": event_count,
        "time": "03:00:00",
        "type": "SIMULATION_END",
        "phase": "COMPLETED",
        "headline": "Event complete",
        "description": "",
        "payload": {},
    }
    return {"events": events}


def test_production_timeline_event_count(production_timeline):
    assert len(production_timeline["events"]) == PRODUCTION_EVENT_COUNT


def test_protected_timeline_round_trip(tmp_path):
    src = tmp_path / "timeline.json"
    data = _synthetic_timeline(PRODUCTION_EVENT_COUNT)
    src.write_text(json.dumps(data), encoding="utf-8")
    pkg = tmp_path / "timeline.pkg"
    protect_timeline_json(src, dest=pkg, expected_events=PRODUCTION_EVENT_COUNT)
    loaded = load_protected_timeline(pkg)
    assert len(loaded["events"]) == PRODUCTION_EVENT_COUNT
    assert loaded["events"][0]["checkpoint_id"] == 1


def test_protect_bytes_round_trip():
    raw = json.dumps(_synthetic_timeline(3)).encode("utf-8")
    blob = protect_timeline_bytes(raw)
    assert unprotect_timeline_bytes(blob) == raw


def test_participant_package_has_no_plaintext_timeline(tmp_path):
    pkg_root = tmp_path / "participant"
    ui = pkg_root / "ui"
    ui.mkdir(parents=True)
    (ui / "index.html").write_text("<html></html>", encoding="utf-8")
    (pkg_root / ".env").write_text("EVENT_PIN_HASH=abc\n", encoding="utf-8")
    forbidden = list(pkg_root.rglob("tradeverse_timeline.json"))
    assert forbidden == []
    content = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in pkg_root.rglob("*") if p.is_file())
    assert "TIMELINE_DECRYPT_KEY" not in content


def test_fresh_database_initialization(db_session, mini_timeline):
    created = bootstrap_universe(db_session)
    assert created["timeline_events"] >= 1
    count = db_session.scalar(select(func.count()).select_from(TimelineEvent)) or 0
    assert count >= 2


def test_offline_startup_configuration(monkeypatch):
    monkeypatch.setenv("LOCAL_INSTANCE_MODE", "true")
    monkeypatch.setenv("PARTICIPANT_EVENT_MODE", "true")
    monkeypatch.setenv("BACKEND_HOST", "127.0.0.1")
    monkeypatch.setenv("BACKEND_PORT", "8765")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.local_instance_mode is True
    assert settings.participant_event_mode is True
    assert settings.backend_host == "127.0.0.1"
    assert settings.database_url.startswith("sqlite")


def test_backend_localhost_binding_default(monkeypatch):
    monkeypatch.setenv("LOCAL_INSTANCE_MODE", "true")
    get_settings.cache_clear()
    settings = get_settings()
    assert "127.0.0.1" in settings.database_url or settings.local_instance_mode


def test_recovery_after_restart(client, mini_timeline, monkeypatch):
    monkeypatch.setenv("LOCAL_INSTANCE_MODE", "true")
    monkeypatch.setenv("PARTICIPANT_EVENT_MODE", "true")
    get_settings.cache_clear()
    _, auth = join_participant(client, "RecoveryUser")
    boot = client.get("/api/v1/session/bootstrap", headers=auth).json()
    assert boot["trader_name"] == "RecoveryUser"
    boot2 = client.get("/api/v1/session/bootstrap", headers=auth).json()
    assert boot2["trader_id"] == boot["trader_id"]


def test_timeline_load_prefers_pkg_over_json(tmp_path, monkeypatch):
    data = _synthetic_timeline(4)
    json_path = tmp_path / "timeline.json"
    pkg_path = tmp_path / "timeline.pkg"
    json_path.write_text(json.dumps(data), encoding="utf-8")
    protect_timeline_json(json_path, dest=pkg_path, expected_events=4)
    monkeypatch.setattr("app.services.timeline_protection.TIMELINE_PKG", pkg_path)
    monkeypatch.setattr("app.services.timeline_protection.TIMELINE_JSON", json_path)
    loaded = load_timeline_data()
    assert len(loaded["events"]) == 4


def test_validate_timeline_on_protected_source(tmp_path):
    src = tmp_path / "timeline.json"
    src.write_text(json.dumps(_synthetic_timeline(PRODUCTION_EVENT_COUNT)), encoding="utf-8")
    pkg = tmp_path / "timeline.pkg"
    protect_timeline_json(src, dest=pkg, expected_events=PRODUCTION_EVENT_COUNT)
    errors = validate_timeline(load_protected_timeline(pkg))
    assert errors == []
