"""Checkpoint jump developer tooling."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.models import TimelineEvent
from app.models.enums import SimulationStatus, TimelineEventStatus
from app.services.simulation_clock import get_or_create_state
from app.services.simulation_controller import reset_simulation, start_simulation
from app.services.timeline_dev_service import jump_to_checkpoint, jump_to_elapsed
from app.services.timeline_service import seed_timeline_from_json


MINI_TIMELINE = {
    "events": [
        {
            "checkpoint_id": 1,
            "time": "00:01",
            "type": "NEWS",
            "phase": "PHASE 1",
            "headline": "Test news one",
            "description": "desc",
            "payload": {"sector_impacts": {"technology": 2.0}},
        },
        {
            "checkpoint_id": 2,
            "time": "00:02",
            "type": "NEWS",
            "phase": "PHASE 1",
            "headline": "Test news two",
            "description": "desc",
            "payload": {"sector_impacts": {"technology": -1.0}},
        },
        {
            "checkpoint_id": 3,
            "time": "03:00:00",
            "type": "SIMULATION_END",
            "phase": "COMPLETED",
            "headline": "Event complete",
            "description": "",
            "payload": {},
        },
    ]
}


@pytest.fixture()
def timeline_db(db_session, monkeypatch):
    os.environ["DEVELOPER_MODE"] = "true"
    get_settings.cache_clear()
    monkeypatch.setattr(
        "app.services.timeline_service.load_timeline_json",
        lambda: MINI_TIMELINE,
    )
    reset_simulation(db_session)
    seed_timeline_from_json(db_session, force=True)
    return db_session


def test_forward_jump_executes_events(timeline_db):
    db = timeline_db
    start_simulation(db)
    result = jump_to_elapsed(db, 120.0, allow_backward=False)
    assert result["events_processed"] >= 1
    executed = db.scalar(
        select(TimelineEvent).where(TimelineEvent.checkpoint_id == 1)
    )
    assert executed is not None
    assert executed.status == TimelineEventStatus.EXECUTED


def test_jump_to_checkpoint_idempotent(timeline_db):
    db = timeline_db
    start_simulation(db)
    jump_to_checkpoint(db, 1, allow_backward=False)
    jump_to_checkpoint(db, 1, allow_backward=False)
    executed = list(
        db.scalars(
            select(TimelineEvent).where(TimelineEvent.checkpoint_id == 1)
        ).all()
    )
    assert len(executed) == 1
    assert executed[0].status == TimelineEventStatus.EXECUTED


def test_backward_jump_resets_and_fast_forwards(timeline_db):
    db = timeline_db
    start_simulation(db)
    jump_to_elapsed(db, 120.0, allow_backward=False)
    state = get_or_create_state(db)
    assert float(state.sim_elapsed_sec) >= 60
    result = jump_to_elapsed(db, 60.0, allow_backward=True)
    assert result["action"] == "jump_backward"
    state2 = get_or_create_state(db)
    assert state2.status == SimulationStatus.PAUSED
