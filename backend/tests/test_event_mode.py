"""Event mode behaviour — PIN gate, no leaderboard, local AI."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ["LOCAL_INSTANCE_MODE"] = "true"
os.environ["PARTICIPANT_EVENT_MODE"] = "true"
os.environ["EVENT_PIN"] = "1234"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from app.core.config import get_settings
from tests.conftest import join_participant, _make_memory_engine
import app.models  # noqa: F401
from app.core.database import Base, get_db
from app.exchange.book_registry import books
from app.main import create_app
from sqlalchemy.orm import sessionmaker


@pytest.fixture()
def event_client() -> TestClient:
    get_settings.cache_clear()
    books.clear()
    engine = _make_memory_engine()
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    Base.metadata.create_all(bind=engine)
    app = create_app()

    def _override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    books.clear()
    get_settings.cache_clear()


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
