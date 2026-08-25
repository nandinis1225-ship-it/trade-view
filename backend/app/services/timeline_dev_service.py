"""Developer-only timeline scrubbing and checkpoint jumps."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import SimulationStatus, TimelineEventStatus
from app.models.timeline_event import TimelineEvent
from app.services.event_processor import process_due_events
from app.services.simulation_clock import advance_clock, get_or_create_state
from app.services.simulation_controller import (
    SimulationControlError,
    reset_simulation,
    start_simulation,
    stop_simulation,
)
from app.services.timeline_service import format_sim_time, progress_snapshot


class TimelineJumpError(Exception):
    pass


def _checkpoint_detail(event: TimelineEvent) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    try:
        payload = json.loads(event.payload_json or "{}")
    except json.JSONDecodeError:
        payload = {}
    return {
        "id": event.id,
        "checkpoint_id": event.checkpoint_id,
        "timestamp": format_sim_time(event.sim_offset_sec),
        "sim_offset_sec": event.sim_offset_sec,
        "phase": event.phase,
        "type": event.event_type.value,
        "headline": event.headline,
        "description": event.description,
        "status": event.status.value,
        "payload": payload,
        "sector_impacts": payload.get("sector_impacts"),
        "market_wide": payload.get("market_wide"),
    }


def developer_timeline_snapshot(db: Session) -> dict[str, Any]:
    state = get_or_create_state(db)
    elapsed = float(state.sim_elapsed_sec)
    progress = progress_snapshot(db, elapsed, include_checkpoints=True)
    events = list(
        db.scalars(
            select(TimelineEvent).order_by(TimelineEvent.sim_offset_sec, TimelineEvent.id)
        ).all()
    )
    progress["checkpoints"] = [_checkpoint_detail(e) for e in events]
    progress["elapsed_sec"] = elapsed
    return progress


def jump_to_elapsed(db: Session, target_sec: float, *, allow_backward: bool = True) -> dict:
    """Jump simulation clock to a checkpoint time for developer testing."""
    if target_sec < 0:
        raise TimelineJumpError("target time must be non-negative")

    state = get_or_create_state(db)
    current = float(state.sim_elapsed_sec)
    target = min(float(state.sim_duration_sec), float(target_sec))

    if target < current:
        if not allow_backward:
            raise TimelineJumpError("backward jumps require allow_backward=true")
        reset_simulation(db)
        return _fast_forward_to(db, target)

    return _forward_jump(db, target)


def jump_to_checkpoint(db: Session, checkpoint_id: int, *, allow_backward: bool = True) -> dict:
    event = db.scalar(select(TimelineEvent).where(TimelineEvent.checkpoint_id == checkpoint_id))
    if event is None:
        raise TimelineJumpError(f"checkpoint {checkpoint_id} not found")
    result = jump_to_elapsed(db, float(event.sim_offset_sec), allow_backward=allow_backward)
    result["checkpoint_id"] = checkpoint_id
    return result


def _forward_jump(db: Session, target_sec: float) -> dict:
    state = get_or_create_state(db)
    original_status = state.status
    was_running = original_status == SimulationStatus.RUNNING

    if original_status == SimulationStatus.COMPLETED:
        raise TimelineJumpError("simulation completed — reset before jumping")

    if not was_running:
        try:
            start_simulation(db)
        except SimulationControlError as exc:
            raise TimelineJumpError(str(exc)) from exc

    state = get_or_create_state(db)
    state.sim_elapsed_sec = target_sec
    db.commit()

    processed = process_due_events(db, target_sec, force=True)

    if not was_running:
        stop_simulation(db)

    state = get_or_create_state(db)
    return {
        "ok": True,
        "action": "jump_forward",
        "target_sec": target_sec,
        "target_time": format_sim_time(target_sec),
        "elapsed_sec": float(state.sim_elapsed_sec),
        "events_processed": len(processed),
        "processed": processed,
        "status": state.status.value,
    }


def _fast_forward_to(db: Session, target_sec: float) -> dict:
    try:
        start_simulation(db)
    except SimulationControlError as exc:
        raise TimelineJumpError(str(exc)) from exc

    state = get_or_create_state(db)
    safety = 0
    while float(state.sim_elapsed_sec) < target_sec and safety < 5000:
        safety += 1
        remaining = target_sec - float(state.sim_elapsed_sec)
        speed = float(state.sim_speed_multiplier or 1.0) or 1.0
        advance_clock(db, remaining / speed)
        process_due_events(db, float(state.sim_elapsed_sec), force=True)
        state = get_or_create_state(db)
        if state.status != SimulationStatus.RUNNING:
            break

    stop_simulation(db)
    state = get_or_create_state(db)
    return {
        "ok": True,
        "action": "jump_backward",
        "target_sec": target_sec,
        "target_time": format_sim_time(target_sec),
        "elapsed_sec": float(state.sim_elapsed_sec),
        "status": state.status.value,
    }


def release_next_news_checkpoint(db: Session) -> dict:
    """Execute the next pending NEWS timeline checkpoint."""
    nxt = db.scalar(
        select(TimelineEvent)
        .where(
            TimelineEvent.status == TimelineEventStatus.PENDING,
            TimelineEvent.event_type == TimelineEventType.NEWS,
        )
        .order_by(TimelineEvent.sim_offset_sec, TimelineEvent.id)
        .limit(1)
    )
    if nxt is None:
        raise TimelineJumpError("no pending news checkpoints")
    return jump_to_checkpoint(db, nxt.checkpoint_id, allow_backward=False)
