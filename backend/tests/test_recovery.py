"""Recovery — wall-clock catch-up and chronological missed-event processing."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models.enums import SimulationStatus, TimelineEventStatus, TimelineEventType
from app.models.timeline_event import TimelineEvent
from app.services.recovery_service import authoritative_elapsed_sec, catch_up_missed_simulation
from app.services.simulation_clock import get_or_create_state
from app.services.simulation_controller import start_simulation


def test_authoritative_elapsed_uses_event_start(db_session, monkeypatch):
    monkeypatch.setenv("PARTICIPANT_EVENT_MODE", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()

    state = get_or_create_state(db_session)
    state.status = SimulationStatus.RUNNING
    state.sim_duration_sec = 10800.0
    state.sim_speed_multiplier = 1.0
    state.anchor_sim_elapsed_sec = 0.0
    state.event_start_real = datetime.now(timezone.utc) - timedelta(seconds=120)
    state.sim_elapsed_sec = 0.0
    db_session.commit()

    elapsed = authoritative_elapsed_sec(state)
    assert 115 <= elapsed <= 125


def test_chronological_recovery_processes_news_and_ai(db_session, monkeypatch):
    monkeypatch.setenv("PARTICIPANT_EVENT_MODE", "true")
    monkeypatch.setenv("LOCAL_INSTANCE_MODE", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()

    start_simulation(db_session)
    state = get_or_create_state(db_session)
    state.last_processed_elapsed_sec = 60.0
    state.last_ai_tick_elapsed_sec = 60.0
    state.sim_elapsed_sec = 60.0
    state.event_start_real = datetime.now(timezone.utc) - timedelta(seconds=90)
    state.anchor_sim_elapsed_sec = 0.0

    db_session.add(
        TimelineEvent(
            checkpoint_id=9001,
            idempotency_key="recovery_test_9001",
            event_type=TimelineEventType.NEWS,
            sim_offset_sec=70.0,
            phase="PHASE 1",
            headline="Recovery headline",
            description="Test news during recovery",
            payload_json='{"sector_impacts":{"financials":2}}',
            status=TimelineEventStatus.PENDING,
        )
    )
    db_session.commit()

    result = catch_up_missed_simulation(db_session)
    assert result["caught_up"] is True
    assert result["events_processed"] >= 1

    event = db_session.scalar(select(TimelineEvent).where(TimelineEvent.checkpoint_id == 9001))
    assert event is not None
    assert event.status == TimelineEventStatus.EXECUTED

    state = get_or_create_state(db_session)
    assert float(state.sim_elapsed_sec) >= 90.0
    assert float(state.last_processed_elapsed_sec) >= 90.0


def test_recovery_does_not_duplicate_executed_events(db_session, monkeypatch):
    monkeypatch.setenv("PARTICIPANT_EVENT_MODE", "true")
    monkeypatch.setenv("LOCAL_INSTANCE_MODE", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()

    start_simulation(db_session)
    state = get_or_create_state(db_session)
    state.last_processed_elapsed_sec = 70.0
    state.last_ai_tick_elapsed_sec = 60.0
    state.sim_elapsed_sec = 70.0
    state.event_start_real = datetime.now(timezone.utc) - timedelta(seconds=100)
    db_session.add(
        TimelineEvent(
            checkpoint_id=9002,
            idempotency_key="recovery_test_9002",
            event_type=TimelineEventType.NEWS,
            sim_offset_sec=70.0,
            phase="PHASE 1",
            headline="Already done",
            description="Executed once",
            payload_json='{"sector_impacts":{"financials":1}}',
            status=TimelineEventStatus.EXECUTED,
        )
    )
    db_session.commit()

    first = catch_up_missed_simulation(db_session)
    second = catch_up_missed_simulation(db_session)
    assert first["events_processed"] >= 0
    assert second["events_processed"] == 0
