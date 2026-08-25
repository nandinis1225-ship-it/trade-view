"""Wall-clock reconciliation and chronological missed-event recovery."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.enums import SimulationStatus, TimelineEventStatus
from app.models.timeline_event import TimelineEvent
from app.services.event_processor import process_single_timeline_event, run_ai_tick_at
from app.services.simulation_clock import get_or_create_state
from app.services.simulation_settings_service import get_or_create_settings

logger = logging.getLogger(__name__)

AI_TICK_INTERVAL_SEC = 30.0


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def authoritative_elapsed_sec(state) -> float:
    """Compute wall-clock authoritative simulation elapsed time."""
    duration = float(state.sim_duration_sec)
    stored = float(state.sim_elapsed_sec)

    if state.status != SimulationStatus.RUNNING:
        return min(duration, max(0.0, stored))

    settings = get_settings()
    if not settings.participant_event_mode:
        return min(duration, max(0.0, stored))

    start = state.event_start_real or state.clock_anchor_real
    if start is None:
        return min(duration, max(0.0, stored))

    now = datetime.now(timezone.utc)
    speed = float(state.sim_speed_multiplier or 1.0)
    anchor_sim = float(state.anchor_sim_elapsed_sec or 0.0)
    wall_elapsed = anchor_sim + (_utc(now) - _utc(start)).total_seconds() * speed
    return min(duration, max(0.0, wall_elapsed))


def _next_ai_tick_after(last_ai_tick: float, after_sec: float, up_to_sec: float) -> float | None:
    if last_ai_tick < 0:
        candidate = AI_TICK_INTERVAL_SEC
    else:
        candidate = last_ai_tick + AI_TICK_INTERVAL_SEC
    while candidate <= after_sec:
        candidate += AI_TICK_INTERVAL_SEC
    if candidate > up_to_sec:
        return None
    return candidate


def _next_pending_event(
    db: Session, after_sec: float, up_to_sec: float
) -> TimelineEvent | None:
    return db.scalar(
        select(TimelineEvent)
        .where(
            TimelineEvent.status == TimelineEventStatus.PENDING,
            TimelineEvent.sim_offset_sec > after_sec,
            TimelineEvent.sim_offset_sec <= up_to_sec,
        )
        .order_by(TimelineEvent.sim_offset_sec, TimelineEvent.id)
        .limit(1)
    )


def catch_up_missed_simulation(db: Session) -> dict:
    """Process missed timeline events and AI ticks chronologically up to wall-clock elapsed."""
    state = get_or_create_state(db)
    settings = get_or_create_settings(db)

    if state.status not in {SimulationStatus.RUNNING, SimulationStatus.COMPLETED}:
        return {"caught_up": False, "reason": state.status.value}

    target = authoritative_elapsed_sec(state)
    cursor = float(state.last_processed_elapsed_sec or 0.0)
    if state.status == SimulationStatus.COMPLETED:
        target = float(state.sim_duration_sec)

    if target <= cursor + 0.001:
        state.sim_elapsed_sec = min(float(state.sim_duration_sec), target)
        db.commit()
        return {
            "caught_up": True,
            "target_sec": target,
            "events_processed": 0,
            "ai_ticks_processed": 0,
        }

    events_processed = 0
    ai_ticks_processed = 0
    safety = 0

    while cursor < target - 0.001 and safety < 10_000:
        safety += 1
        state = get_or_create_state(db)
        last_ai = float(state.last_ai_tick_elapsed_sec)
        next_event = _next_pending_event(db, cursor, target)
        next_ai = (
            _next_ai_tick_after(last_ai, cursor, target)
            if settings.simulation_ai_enabled
            else None
        )

        if next_event is not None and (
            next_ai is None or float(next_event.sim_offset_sec) <= next_ai
        ):
            event_time = float(next_event.sim_offset_sec)
            process_single_timeline_event(db, next_event, event_time)
            state = get_or_create_state(db)
            state.sim_elapsed_sec = event_time
            state.last_processed_elapsed_sec = event_time
            cursor = event_time
            events_processed += 1
            db.commit()
            continue

        if next_ai is not None:
            run_ai_tick_at(db, next_ai)
            state = get_or_create_state(db)
            state.sim_elapsed_sec = next_ai
            state.last_processed_elapsed_sec = next_ai
            cursor = next_ai
            ai_ticks_processed += 1
            db.commit()
            continue

        break

    state = get_or_create_state(db)
    state.sim_elapsed_sec = target
    state.last_processed_elapsed_sec = target

    if target >= float(state.sim_duration_sec) and state.status == SimulationStatus.RUNNING:
        from app.services.simulation_engine import session_pause

        state.status = SimulationStatus.COMPLETED
        session_pause(db)
        logger.info("Simulation completed during recovery at sim=%.0fs", target)

    db.commit()
    logger.info(
        "Recovery catch-up: target=%.0fs events=%s ai_ticks=%s",
        target,
        events_processed,
        ai_ticks_processed,
    )
    return {
        "caught_up": True,
        "target_sec": target,
        "events_processed": events_processed,
        "ai_ticks_processed": ai_ticks_processed,
    }


def reconcile_on_startup(db: Session) -> dict:
    """Called at backend startup and session bootstrap before serving state."""
    state = get_or_create_state(db)
    if state.status != SimulationStatus.RUNNING:
        return {"reconciled": False, "status": state.status.value}
    return catch_up_missed_simulation(db)
