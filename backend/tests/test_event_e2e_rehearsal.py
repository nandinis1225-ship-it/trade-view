"""End-to-end accelerated rehearsal on the production timeline (when available)."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.models import TimelineEvent
from app.models.enums import SimulationStatus, TimelineEventStatus
from app.services.event_processor import process_due_events
from app.services.recovery_service import reconcile_on_startup
from app.services.simulation_controller import reset_simulation, start_simulation
from app.services.simulation_clock import advance_clock, get_or_create_state
from app.services.simulation_settings_service import update_settings
from app.services.timeline_protection import TIMELINE_PKG
from app.services.timeline_service import seed_timeline_from_json, validate_timeline
from tests.conftest import join_participant


@pytest.mark.skipif(not TIMELINE_PKG.is_file(), reason="tradeverse_timeline.pkg required")
def test_production_timeline_e2e_accelerated_rehearsal(db_session, production_timeline, client):
    """Accelerated rehearsal: production timeline validates and completes without duplicate events."""
    errors = validate_timeline(production_timeline)
    assert errors == [], errors
    assert len(production_timeline["events"]) == 64

    seed_timeline_from_json(db_session, force=True)
    reset_simulation(db_session)
    update_settings(db_session, sim_speed_multiplier=60.0)
    start_simulation(db_session)

    total = db_session.scalar(select(func.count(TimelineEvent.id))) or 0
    assert total == 64

    for _ in range(400):
        state = get_or_create_state(db_session)
        if state.status == SimulationStatus.COMPLETED:
            break
        advance_clock(db_session, 60.0 / float(state.sim_speed_multiplier or 1))
        state = get_or_create_state(db_session)
        process_due_events(db_session, float(state.sim_elapsed_sec))
        if float(state.sim_elapsed_sec) >= float(state.sim_duration_sec):
            process_due_events(db_session, float(state.sim_duration_sec))
            state.status = SimulationStatus.COMPLETED
            db_session.commit()
            break

    executed = db_session.scalar(
        select(func.count(TimelineEvent.id)).where(
            TimelineEvent.status == TimelineEventStatus.EXECUTED
        )
    ) or 0
    assert executed == total
    assert get_or_create_state(db_session).status == SimulationStatus.COMPLETED


@pytest.mark.skipif(not TIMELINE_PKG.is_file(), reason="tradeverse_timeline.pkg required")
def test_production_recovery_replays_without_duplicates(db_session, production_timeline):
    seed_timeline_from_json(db_session, force=True)
    reset_simulation(db_session)
    start_simulation(db_session)
    process_due_events(db_session, 120.0)
    first_executed = db_session.scalar(
        select(func.count(TimelineEvent.id)).where(
            TimelineEvent.status == TimelineEventStatus.EXECUTED
        )
    ) or 0
    assert first_executed >= 1

    reconcile_on_startup(db_session)
    second_executed = db_session.scalar(
        select(func.count(TimelineEvent.id)).where(
            TimelineEvent.status == TimelineEventStatus.EXECUTED
        )
    ) or 0
    assert second_executed == first_executed


@pytest.mark.skipif(not TIMELINE_PKG.is_file(), reason="tradeverse_timeline.pkg required")
def test_participant_join_and_bootstrap_on_production_timeline(production_timeline, event_client):
    _, auth = join_participant(event_client, "E2EUser")
    boot = event_client.get("/api/v1/session/bootstrap", headers=auth).json()
    assert boot["trader_name"] == "E2EUser"
    assert "simulation" in boot
