"""Phase 5 accelerated rehearsal — full event duration at high sim speed (mini timeline)."""

from __future__ import annotations

from sqlalchemy import func, select

from app.models import TimelineEvent
from app.models.enums import SimulationStatus, TimelineEventStatus
from app.services.event_processor import process_due_events
from app.services.recovery_service import catch_up_missed_simulation
from app.services.simulation_controller import reset_simulation, start_simulation
from app.services.simulation_clock import advance_clock, get_or_create_state
from app.services.simulation_settings_service import update_settings
from app.services.timeline_service import seed_timeline_from_json


def test_accelerated_rehearsal_completes_mini_event_at_60x(db_session, mini_timeline):
    """Rehearsal gate: 3h sim completes with all timeline events executed once."""
    seed_timeline_from_json(db_session, force=True)
    reset_simulation(db_session)
    update_settings(db_session, sim_speed_multiplier=60.0)
    start_simulation(db_session)

    total = db_session.scalar(select(func.count(TimelineEvent.id))) or 0
    assert total >= 2

    for _ in range(500):
        state = get_or_create_state(db_session)
        if state.status == SimulationStatus.COMPLETED:
            break
        catch_up_missed_simulation(db_session)
        state = get_or_create_state(db_session)
        process_due_events(db_session, float(state.sim_elapsed_sec))
        advance_clock(db_session, 1.0)
        state = get_or_create_state(db_session)
        if float(state.sim_elapsed_sec) >= float(state.sim_duration_sec):
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
