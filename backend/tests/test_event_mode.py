"""Event mode behaviour — PIN gate, no leaderboard, local AI."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import join_participant


def test_validate_pin_accepts_correct(event_client: TestClient):
    res = event_client.post("/api/v1/auth/validate-pin", json={"pin": "1234"})
    assert res.status_code == 200
    assert res.json()["ok"] is True


def test_validate_pin_rejects_wrong(event_client: TestClient):
    res = event_client.post("/api/v1/auth/validate-pin", json={"pin": "9999"})
    assert res.status_code == 403


def test_participant_cannot_stop_in_event_mode(event_client: TestClient):
    res = event_client.post("/api/v1/simulation/stop")
    assert res.status_code == 403


def test_participant_cannot_reset_in_event_mode(event_client: TestClient):
    res = event_client.post("/api/v1/simulation/reset")
    assert res.status_code == 403


def test_bootstrap_has_no_leaderboard_in_event_mode(event_client: TestClient):
    _, auth = join_participant(event_client, "EventUser")
    body = event_client.get("/api/v1/session/bootstrap", headers=auth).json()
    assert "leaderboard" not in body
    assert "trade_count" in body


def test_health_reports_event_mode(event_client: TestClient):
    body = event_client.get("/api/v1/health").json()
    assert body["participant_event_mode"] is True
    assert body["pin_required"] is True
