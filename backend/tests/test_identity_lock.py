# Phase 2 identity lock tests

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from tests.conftest import join_participant


def test_identity_lock_rejects_name_change(event_client: TestClient):
    first_id, first_auth = join_participant(event_client, "Alice", session_id="sess-lock-1")
    second = event_client.post(
        "/api/v1/auth/join",
        json={"display_name": "Bob", "session_id": "sess-lock-2"},
    )
    assert second.status_code == 403

    _, resume_auth = join_participant(event_client, "Alice", session_id="sess-lock-1")
    body = event_client.get("/api/v1/session/bootstrap", headers=resume_auth).json()
    assert body["trader_name"] == "Alice"
    assert body["trader_id"] == first_id


def test_leaderboard_disabled_in_event_mode(event_client: TestClient):
    res = event_client.get("/api/v1/leaderboard")
    assert res.status_code == 404
