"""Developer mode route gating."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.config import get_settings
from app.core.database import Base, get_db
from app.exchange.book_registry import books
from app.main import create_app


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


def _client_with_dev_flag(dev_mode: bool) -> TestClient:
    os.environ["DEVELOPER_MODE"] = "true" if dev_mode else "false"
    os.environ["LOCAL_INSTANCE_MODE"] = "true"
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
    return TestClient(app)


def test_developer_routes_hidden_when_disabled():
    client = _client_with_dev_flag(False)
    try:
        assert client.get("/api/v1/developer/simulation/status").status_code == 404
        assert client.get("/api/v1/admin/simulation/status").status_code == 404
        assert client.post("/api/v1/simulation/organizer/stop", json={"passkey": "x"}).status_code == 404
        assert client.get("/docs").status_code == 404
    finally:
        get_settings.cache_clear()


def test_developer_routes_available_when_enabled():
    client = _client_with_dev_flag(True)
    try:
        res = client.get("/api/v1/developer/simulation/status")
        assert res.status_code == 200, res.text
        assert client.get("/docs").status_code == 200
    finally:
        get_settings.cache_clear()
