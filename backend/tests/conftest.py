"""Shared pytest fixtures — in-memory SQLite so tests need no Postgres."""

from __future__ import annotations

import os
from typing import Any

import app.models  # noqa: F401 — register metadata
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.database import Base, get_db
from app.exchange.book_registry import books
from app.main import create_app

# TEST ONLY — mini timeline for fast unit/integration tests. Not the production timeline.
TEST_TIMELINE_MINI: dict[str, Any] = {
    "events": [
        {
            "checkpoint_id": 1,
            "time": "00:01",
            "type": "NEWS",
            "phase": "PHASE 1",
            "headline": "Test news",
            "description": "desc",
            "payload": {"sector_impacts": {"technology": 2.0}},
        },
        {
            "checkpoint_id": 2,
            "time": "03:00:00",
            "type": "SIMULATION_END",
            "phase": "COMPLETED",
            "headline": "Event complete",
            "description": "",
            "payload": {},
        },
    ]
}


def _patch_timeline(monkeypatch, timeline: dict[str, Any]) -> None:
    from app.services import timeline_service

    monkeypatch.setattr(timeline_service, "load_timeline_json", lambda: timeline)
    monkeypatch.setattr(
        "app.services.timeline_crypto.load_timeline_data",
        lambda _key=None: timeline,
    )


@pytest.fixture()
def mini_timeline(monkeypatch):
    """TEST ONLY — patch timeline loaders with a 2-event mini fixture."""
    _patch_timeline(monkeypatch, TEST_TIMELINE_MINI)
    return TEST_TIMELINE_MINI


@pytest.fixture()
def production_timeline(monkeypatch):
    """Load the real encrypted production timeline (requires TIMELINE_DECRYPT_KEY)."""
    from app.services.timeline_crypto import TIMELINE_ENC, decrypt_timeline_bytes

    key = os.environ.get("TIMELINE_DECRYPT_KEY")
    if not key:
        pytest.skip("TIMELINE_DECRYPT_KEY required for production timeline tests")
    if not TIMELINE_ENC.is_file():
        pytest.skip("tradeverse_timeline.enc not found")
    data = decrypt_timeline_bytes(key, TIMELINE_ENC.read_bytes())
    _patch_timeline(monkeypatch, data)
    return data


def join_participant(
    client: TestClient, display_name: str = "Tester", session_id: str | None = None
) -> tuple[int, dict[str, str]]:
    payload: dict[str, str] = {"display_name": display_name}
    if session_id is not None:
        payload["session_id"] = session_id
    res = client.post("/api/v1/auth/join", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    return data["trader_id"], headers


def _make_memory_engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


@pytest.fixture()
def db_session() -> Session:
    os.environ["DEVELOPER_MODE"] = "true"
    os.environ["PARTICIPANT_EVENT_MODE"] = "false"
    get_settings.cache_clear()
    books.clear()
    engine = _make_memory_engine()
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    try:
        from app.models.enums import SimulationStatus
        from app.services.simulation_clock import get_or_create_state

        state = get_or_create_state(session)
        state.status = SimulationStatus.RUNNING
        session.commit()
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        books.clear()
        get_settings.cache_clear()


@pytest.fixture()
def client() -> TestClient:
    os.environ["DEVELOPER_MODE"] = "true"
    os.environ["PARTICIPANT_EVENT_MODE"] = "false"
    get_settings.cache_clear()
    books.clear()
    engine = _make_memory_engine()
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    Base.metadata.create_all(bind=engine)

    app = create_app()
    settings = get_settings()

    def _override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_db
    headers = {"Authorization": f"Bearer {settings.admin_secret}"}
    with TestClient(app, headers=headers) as test_client:
        db = TestingSession()
        from app.models.enums import SimulationStatus
        from app.services.simulation_clock import get_or_create_state

        state = get_or_create_state(db)
        state.status = SimulationStatus.RUNNING
        db.commit()
        db.close()
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    books.clear()
    get_settings.cache_clear()


@pytest.fixture()
def event_client() -> TestClient:
    os.environ["LOCAL_INSTANCE_MODE"] = "true"
    os.environ["DEVELOPER_MODE"] = "false"
    os.environ["PARTICIPANT_EVENT_MODE"] = "true"
    os.environ["EVENT_PIN"] = "1234"
    os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
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
