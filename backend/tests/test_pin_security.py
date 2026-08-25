"""Tests for local PIN hash verification."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.services.pin_service import generate_pin_verifier, verify_event_pin


@pytest.fixture()
def event_client() -> TestClient:
    os.environ["LOCAL_INSTANCE_MODE"] = "true"
    os.environ["PARTICIPANT_EVENT_MODE"] = "true"
    os.environ["EVENT_PIN"] = "1234"
    os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
    from app.core.config import get_settings
    from tests.conftest import _make_memory_engine
    import app.models  # noqa: F401
    from app.core.database import Base, get_db
    from app.exchange.book_registry import books
    from app.main import create_app
    from sqlalchemy.orm import sessionmaker

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


def test_pin_hash_roundtrip(monkeypatch):
    monkeypatch.setenv("EVENT_PIN", "")
    monkeypatch.setenv("EVENT_PIN_SALT", "")
    monkeypatch.setenv("EVENT_PIN_HASH", "")
    from app.core.config import get_settings

    get_settings.cache_clear()
    salt, digest = generate_pin_verifier("5678")
    monkeypatch.setenv("EVENT_PIN_SALT", salt)
    monkeypatch.setenv("EVENT_PIN_HASH", digest)
    get_settings.cache_clear()
    assert verify_event_pin("5678") is True
    assert verify_event_pin("0000") is False


def test_validate_pin_with_hash(event_client: TestClient, monkeypatch):
    salt, digest = generate_pin_verifier("1234")
    monkeypatch.setenv("EVENT_PIN", "")
    monkeypatch.setenv("EVENT_PIN_SALT", salt)
    monkeypatch.setenv("EVENT_PIN_HASH", digest)
    from app.core.config import get_settings

    get_settings.cache_clear()
    res = event_client.post("/api/v1/auth/validate-pin", json={"pin": "1234"})
    assert res.status_code == 200
