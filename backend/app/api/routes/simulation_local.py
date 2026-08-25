"""Participant simulation control (local instance mode)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import require_trader
from app.models import Trader
from app.services.leaderboard_sync_service import (
    build_snapshot_payload,
    clear_supabase_leaderboard,
    push_snapshot,
    signal_global_reset,
)
from app.services.fresh_wipe_service import FreshWipeError, fresh_wipe_local_db
from app.services.participant_package_service import ParticipantPackageError, build_participant_zip
from app.services.simulation_controller import (
    SimulationControlError,
    bootstrap_universe,
    reset_simulation,
    start_simulation,
    stop_simulation,
)
from app.services import news_service, sector_service
from app.services.simulation_clock import participant_sim_control_response, participant_status_dict, status_dict

router = APIRouter(prefix="/simulation", tags=["simulation"])


class OrganizerResetBody(BaseModel):
    passkey: str = Field(min_length=1)


class EventStartBody(BaseModel):
    event_pin: str = Field(min_length=1, max_length=32)


def _require_event_mode() -> None:
    if not get_settings().participant_event_mode:
        raise HTTPException(status_code=404, detail="event mode disabled")


def _validate_event_pin(pin: str) -> None:
    expected = (get_settings().event_pin or "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="event pin not configured")
    if pin.strip() != expected:
        raise HTTPException(status_code=403, detail="invalid event pin")


def _require_local_mode() -> None:
    if not get_settings().local_instance_mode:
        raise HTTPException(status_code=404, detail="local simulation API disabled")


def _require_organizer_client(request: Request) -> None:
    host = request.client.host if request.client else ""
    if host not in ("127.0.0.1", "::1", "localhost"):
        raise HTTPException(status_code=403, detail="organizer actions only from this computer")


def _require_organizer_passkey(body: OrganizerResetBody) -> None:
    if body.passkey != get_settings().organizer_passkey:
        raise HTTPException(status_code=403, detail="invalid organizer passkey")


def _participant_sim_response(db: Session, result: dict) -> dict:
    """Strip internal simulation metadata from control responses."""
    return participant_sim_control_response(db, result)


@router.get("/status")
def simulation_status(db: Session = Depends(get_db)) -> dict:
    _require_local_mode()
    return participant_status_dict(db)


@router.post("/bootstrap")
def simulation_bootstrap(db: Session = Depends(get_db)) -> dict:
    _require_local_mode()
    return bootstrap_universe(db)


@router.post("/start")
def simulation_start(db: Session = Depends(get_db)) -> dict:
    _require_local_mode()
    if get_settings().participant_event_mode:
        raise HTTPException(status_code=403, detail="use /simulation/event-start in event mode")
    try:
        return _participant_sim_response(db, start_simulation(db))
    except SimulationControlError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/event-start")
def simulation_event_start(
    body: EventStartBody,
    db: Session = Depends(get_db),
) -> dict:
    """Event mode: validate PIN locally and auto-start the simulation."""
    _require_local_mode()
    _require_event_mode()
    _validate_event_pin(body.event_pin)
    try:
        return _participant_sim_response(db, start_simulation(db))
    except SimulationControlError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/stop")
def simulation_stop(db: Session = Depends(get_db)) -> dict:
    _require_local_mode()
    if get_settings().participant_event_mode:
        raise HTTPException(status_code=403, detail="participants cannot stop the simulation")
    try:
        return _participant_sim_response(db, stop_simulation(db))
    except SimulationControlError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/reset")
def simulation_reset(db: Session = Depends(get_db)) -> dict:
    _require_local_mode()
    if get_settings().participant_event_mode:
        raise HTTPException(status_code=403, detail="participants cannot reset the simulation")
    try:
        return _participant_sim_response(db, reset_simulation(db))
    except SimulationControlError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/organizer/stop")
async def organizer_stop(
    body: OrganizerResetBody,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Organizer-only: pause the market clock on this laptop."""
    _require_local_mode()
    _require_organizer_client(request)
    _require_organizer_passkey(body)
    try:
        return stop_simulation(db)
    except SimulationControlError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/organizer/reset-all")
async def organizer_reset_all(
    body: OrganizerResetBody,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Organizer-only: reset local market, signal all participants, clear cloud leaderboard."""
    _require_local_mode()
    _require_organizer_client(request)
    _require_organizer_passkey(body)
    try:
        result = reset_simulation(db)
    except SimulationControlError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    signaled = await signal_global_reset()
    cleared = await clear_supabase_leaderboard()
    return {
        **result,
        "global_reset_signaled": signaled,
        "leaderboard_cleared": cleared,
    }


@router.post("/organizer/fresh-wipe")
async def organizer_fresh_wipe(
    body: OrganizerResetBody,
    request: Request,
) -> dict:
    """Organizer-only: delete local SQLite + caches, signal everyone to rejoin."""
    _require_local_mode()
    _require_organizer_client(request)
    _require_organizer_passkey(body)
    try:
        result = fresh_wipe_local_db()
    except FreshWipeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    signaled = await signal_global_reset()
    cleared = await clear_supabase_leaderboard()
    return {
        **result,
        "global_reset_signaled": signaled,
        "leaderboard_cleared": cleared,
        "clients_should_rejoin": True,
    }


@router.post("/organizer/build-participant-zip")
async def organizer_build_participant_zip(
    body: OrganizerResetBody,
    request: Request,
) -> dict:
    """Organizer-only: build Tradeverse-Participant.zip in the project folder."""
    _require_local_mode()
    _require_organizer_client(request)
    _require_organizer_passkey(body)
    try:
        return build_participant_zip()
    except ParticipantPackageError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/organizer/market-dashboard")
async def organizer_market_dashboard(
    body: OrganizerResetBody,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Organizer-only: full market view with phase and sector impacts for projector."""
    _require_local_mode()
    _require_organizer_client(request)
    _require_organizer_passkey(body)
    clock = status_dict(db)
    change = sector_service.market_change_pct(db)
    events = news_service.list_news(db, released_only=True)
    latest = None
    if events:
        detail = news_service.news_detail_dict(events[0])
        latest = {
            "id": detail["id"],
            "title": detail["title"],
            "description": detail["description"],
            "released_at": detail["released_at"],
            "sector_impacts": detail["sector_impacts"],
        }
    news_items = []
    for event in news_service.list_news(db, released_only=True):
        detail = news_service.news_detail_dict(event)
        news_items.append(
            {
                "id": detail["id"],
                "title": detail["title"],
                "description": detail["description"],
                "released_at": detail["released_at"],
                "sector_impacts": detail["sector_impacts"],
            }
        )
    return {
        "elapsed": clock["elapsed"],
        "current_phase": clock["current_phase"],
        "status": clock["status"],
        "market_change_pct": str(change),
        "latest_news": latest,
        "news": news_items,
    }


@router.post("/export-snapshot")
async def export_snapshot(
    db: Session = Depends(get_db),
    trader: Trader = Depends(require_trader),
) -> dict:
    _require_local_mode()
    if get_settings().participant_event_mode:
        raise HTTPException(status_code=404, detail="export disabled in event mode")
    payload = build_snapshot_payload(db, trader.id)
    await push_snapshot(trader.id)
    return payload
