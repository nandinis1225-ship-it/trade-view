"""Developer-only testing and inspection routes (localhost, DEVELOPER_MODE)."""

from __future__ import annotations

import json
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.ai import runner as ai_runner
from app.core.database import get_db
from app.core.developer_guard import require_local_developer
from app.models import (
    AIAgent,
    Holding,
    IPO,
    IPOApplication,
    Order,
    SimulationEventLog,
    Stock,
    TimelineEvent,
    Trade,
    Trader,
)
from app.models.enums import TimelineEventStatus, TimelineEventType, TraderType
from app.models.order_enums import OrderStatus
from app.realtime.ws_manager import manager
from app.services import ipo_service, news_service, sector_service, stock_service
from app.services.simulation_clock import get_or_create_state, status_dict
from app.services.simulation_controller import (
    SimulationControlError,
    reset_simulation,
    start_simulation,
    stop_simulation,
)
from app.services.simulation_settings_service import (
    get_or_create_settings,
    settings_dict,
    sync_runtime_speed_from_settings,
    update_settings,
)
from app.services.timeline_dev_service import (
    TimelineJumpError,
    developer_timeline_snapshot,
    jump_to_checkpoint,
    jump_to_elapsed,
    release_next_news_checkpoint,
)
from app.services.timeline_service import progress_snapshot
from app.schemas.orders import SimulationSettingsUpdate

router = APIRouter(prefix="/developer", tags=["developer"])


class JumpBody(BaseModel):
    target_sec: float | None = None
    checkpoint_id: int | None = None
    allow_backward: bool = True


class SpeedBody(BaseModel):
    sim_speed_multiplier: float = Field(gt=0, le=3600)


def _sim_action(db: Session, action: str) -> dict:
    try:
        if action == "start":
            result = start_simulation(db)
        elif action == "stop":
            result = stop_simulation(db)
        elif action == "resume":
            result = start_simulation(db)
        elif action == "reset":
            result = reset_simulation(db)
        elif action == "restart":
            reset_simulation(db)
            result = start_simulation(db)
        else:
            raise HTTPException(400, f"unknown action: {action}")
    except SimulationControlError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    return result


@router.get("/simulation/status")
def dev_simulation_status(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    require_local_developer(request)
    state = status_dict(db)
    progress = progress_snapshot(db, state["elapsed_sec"], include_checkpoints=True)
    return {**state, **progress}


@router.post("/simulation/{action}")
async def dev_simulation_control(
    action: str,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    require_local_developer(request)
    if action not in ("start", "stop", "resume", "reset", "restart"):
        raise HTTPException(404, detail="unknown action")
    result = _sim_action(db, action)
    await manager.broadcast("SIMULATION_STATUS", status_dict(db))
    return result


@router.patch("/simulation/speed")
def dev_set_speed(
    body: SpeedBody,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    require_local_developer(request)
    row = update_settings(db, sim_speed_multiplier=body.sim_speed_multiplier)
    state = get_or_create_state(db)
    state.sim_speed_multiplier = float(body.sim_speed_multiplier)
    db.commit()
    return {"ok": True, **settings_dict(row), **status_dict(db)}


@router.get("/simulation/settings")
def dev_get_settings(request: Request, db: Session = Depends(get_db)) -> dict:
    require_local_developer(request)
    return settings_dict(get_or_create_settings(db))


@router.patch("/simulation/settings")
def dev_patch_settings(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    require_local_developer(request)
    parsed = SimulationSettingsUpdate.model_validate(payload)
    row = update_settings(db, **parsed.model_dump(exclude_unset=True))
    sync_runtime_speed_from_settings(db)
    return settings_dict(row)


@router.get("/timeline")
def dev_timeline(request: Request, db: Session = Depends(get_db)) -> dict:
    require_local_developer(request)
    return developer_timeline_snapshot(db)


@router.post("/timeline/jump")
async def dev_timeline_jump(
    body: JumpBody,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    require_local_developer(request)
    try:
        if body.checkpoint_id is not None:
            result = jump_to_checkpoint(
                db, body.checkpoint_id, allow_backward=body.allow_backward
            )
        elif body.target_sec is not None:
            result = jump_to_elapsed(db, body.target_sec, allow_backward=body.allow_backward)
        else:
            raise HTTPException(400, detail="checkpoint_id or target_sec required")
    except TimelineJumpError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    await manager.broadcast("SIMULATION_STATUS", status_dict(db))
    return result


@router.post("/news/release-next")
async def dev_release_next_news(request: Request, db: Session = Depends(get_db)) -> dict:
    require_local_developer(request)
    try:
        result = release_next_news_checkpoint(db)
    except TimelineJumpError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    await manager.broadcast("SIMULATION_STATUS", status_dict(db))
    return result


@router.get("/news")
def dev_list_news(request: Request, db: Session = Depends(get_db)) -> list[dict]:
    require_local_developer(request)
    from app.services.news_service import effective_impact

    out = []
    for event in news_service.list_news(db, include_scheduled=True):
        out.append(
            {
                "id": event.id,
                "title": event.title,
                "description": event.description,
                "status": event.status,
                "released_at": event.released_at.isoformat() if event.released_at else None,
                "effective_impact": effective_impact(event),
            }
        )
    return out


@router.get("/logs")
def dev_logs(
    request: Request,
    db: Session = Depends(get_db),
    event_type: str | None = None,
    since: float | None = None,
    limit: int = Query(default=200, le=1000),
) -> list[dict]:
    require_local_developer(request)
    q = select(SimulationEventLog).order_by(SimulationEventLog.id.desc()).limit(limit)
    if event_type:
        q = q.where(SimulationEventLog.event_type == event_type)
    if since is not None:
        q = q.where(SimulationEventLog.sim_elapsed_sec >= since)
    rows = list(db.scalars(q).all())
    out = []
    for row in reversed(rows):
        try:
            detail = json.loads(row.detail_json or "{}")
        except json.JSONDecodeError:
            detail = {"raw": row.detail_json}
        out.append(
            {
                "id": row.id,
                "sim_elapsed_sec": row.sim_elapsed_sec,
                "event_type": row.event_type,
                "detail": detail,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )
    return out


@router.get("/market-state")
def dev_market_state(request: Request, db: Session = Depends(get_db)) -> dict:
    require_local_developer(request)
    stocks = stock_service.list_stocks(db)
    sectors = sector_service.list_sectors(db)
    open_orders = list(
        db.scalars(
            select(Order)
            .where(Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED]))
            .order_by(Order.id.desc())
            .limit(100)
        ).all()
    )
    trades = list(db.scalars(select(Trade).order_by(Trade.id.desc()).limit(100)).all())
    return {
        "stocks": [
            {
                "id": s.id,
                "ticker": s.ticker,
                "company_name": s.company_name,
                "sector_id": s.sector_id,
                "last_price": str(s.last_traded_price),
                "starting_price": str(s.starting_price),
                "pct_change": float(
                    (s.last_traded_price - s.starting_price) / s.starting_price * 100
                    if s.starting_price
                    else 0
                ),
                "is_open": s.is_open,
                "is_halted": s.is_halted,
                "status": s.status,
            }
            for s in stocks
        ],
        "sectors": [
            {
                "id": sec.id,
                "name": sec.name,
                "slug": sec.slug,
            }
            for sec in sectors
        ],
        "open_orders": [
            {
                "id": o.id,
                "trader_id": o.trader_id,
                "stock_id": o.stock_id,
                "side": o.side.value,
                "quantity": o.quantity,
                "filled_quantity": o.filled_quantity,
                "status": o.status.value,
            }
            for o in open_orders
        ],
        "recent_trades": [
            {
                "id": t.id,
                "stock_id": t.stock_id,
                "price": str(t.price),
                "quantity": t.quantity,
                "buyer_id": t.buyer_trader_id,
                "seller_id": t.seller_trader_id,
            }
            for t in trades
        ],
    }


@router.get("/portfolio/{trader_id}")
def dev_portfolio(
    trader_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    require_local_developer(request)
    trader = db.get(Trader, trader_id)
    if not trader:
        raise HTTPException(404, detail="trader not found")
    holdings = list(
        db.scalars(
            select(Holding)
            .where(Holding.trader_id == trader_id)
            .options(joinedload(Holding.stock))
        ).all()
    )
    trades = list(
        db.scalars(
            select(Trade)
            .where((Trade.buyer_trader_id == trader_id) | (Trade.seller_trader_id == trader_id))
            .order_by(Trade.id.desc())
            .limit(50)
        ).all()
    )
    ipo_apps = [_ipo_app_dict(a) for a in ipo_service.list_applications(db, trader_id=trader_id)]
    portfolio_value = Decimal(trader.cash)
    for h in holdings:
        if h.stock:
            portfolio_value += Decimal(h.quantity) * Decimal(h.stock.last_traded_price)
    return {
        "trader": {
            "id": trader.id,
            "name": trader.name,
            "cash": str(trader.cash),
            "cash_blocked_ipo": str(trader.cash_blocked_ipo),
            "realized_pnl": str(trader.realized_pnl),
        },
        "holdings": [
            {
                "stock_id": h.stock_id,
                "ticker": h.stock.ticker if h.stock else None,
                "quantity": h.quantity,
                "avg_cost": str(h.avg_cost),
            }
            for h in holdings
        ],
        "portfolio_value": str(portfolio_value),
        "trades": [
            {
                "id": t.id,
                "stock_id": t.stock_id,
                "price": str(t.price),
                "quantity": t.quantity,
                "side": "buy" if t.buyer_trader_id == trader_id else "sell",
            }
            for t in trades
        ],
        "ipo_applications": ipo_apps,
    }


def _ipo_app_dict(app: IPOApplication) -> dict:
    return {
        "id": app.id,
        "ipo_id": app.ipo_id,
        "requested_lots": app.requested_lots,
        "allocated_lots": app.allocated_lots,
        "amount_blocked": str(app.amount_blocked),
        "amount_used": str(app.amount_used),
        "status": app.status.value,
    }


@router.get("/ai/state")
def dev_ai_state(request: Request, db: Session = Depends(get_db)) -> dict:
    require_local_developer(request)
    state = get_or_create_state(db)
    agents = list(db.scalars(select(AIAgent)).all())
    ai_orders = list(
        db.scalars(
            select(Order)
            .join(Trader, Order.trader_id == Trader.id)
            .where(Trader.trader_type == TraderType.AI)
            .order_by(Order.id.desc())
            .limit(50)
        ).all()
    )
    settings = get_or_create_settings(db)
    return {
        "simulation_ai_enabled": settings.simulation_ai_enabled,
        "last_ai_tick_elapsed_sec": float(state.last_ai_tick_elapsed_sec),
        "agents": [
            {
                "id": a.id,
                "strategy": a.strategy,
                "is_enabled": a.is_enabled,
                "trader_id": a.trader_id,
            }
            for a in agents
        ],
        "recent_ai_orders": [
            {
                "id": o.id,
                "trader_id": o.trader_id,
                "stock_id": o.stock_id,
                "side": o.side.value,
                "status": o.status.value,
            }
            for o in ai_orders
        ],
    }


@router.post("/ai/seed")
def dev_ai_seed(request: Request, db: Session = Depends(get_db)) -> dict:
    require_local_developer(request)
    created = ai_runner.seed_default_agents(db)
    synced = ai_runner.sync_intensity_configs(db)
    return {"created": created, "configs_synced": synced}


@router.post("/ai/tick")
async def dev_ai_tick(request: Request, db: Session = Depends(get_db)) -> dict:
    require_local_developer(request)
    results = ai_runner.run_all_agents(db)
    return {"actions": len(results), "results": results[:50]}


@router.get("/ipos")
def dev_list_ipos(request: Request, db: Session = Depends(get_db)) -> list[dict]:
    require_local_developer(request)
    return [_ipo_dict(i) for i in ipo_service.list_ipos(db)]


def _ipo_dict(ipo: IPO) -> dict:
    return {
        "id": ipo.id,
        "company_name": ipo.company_name,
        "ticker": ipo.ticker,
        "status": ipo.status.value,
        "issue_price": str(ipo.issue_price),
        "total_lots": ipo.total_lots,
        "stock_id": ipo.stock_id,
    }


@router.get("/ipos/{ipo_id}/applications")
def dev_ipo_apps(ipo_id: int, request: Request, db: Session = Depends(get_db)) -> list[dict]:
    require_local_developer(request)
    return [_ipo_app_dict(a) for a in ipo_service.list_applications(db, ipo_id=ipo_id)]


@router.get("/dissolution/upcoming")
def dev_dissolution_upcoming(request: Request, db: Session = Depends(get_db)) -> list[dict]:
    require_local_developer(request)
    events = list(
        db.scalars(
            select(TimelineEvent)
            .where(
                TimelineEvent.event_type == TimelineEventType.COMPANY_DISSOLUTION,
                TimelineEvent.status == TimelineEventStatus.PENDING,
            )
            .order_by(TimelineEvent.sim_offset_sec)
        ).all()
    )
    return [_checkpoint_detail_dev(e) for e in events]


def _checkpoint_detail_dev(event: TimelineEvent) -> dict:
    payload = json.loads(event.payload_json or "{}")
    return {
        "checkpoint_id": event.checkpoint_id,
        "timestamp": event.sim_offset_sec,
        "headline": event.headline,
        "ticker": payload.get("ticker"),
        "liquidation_price": payload.get("liquidation_price"),
        "status": event.status.value,
    }


@router.get("/traders")
def dev_list_traders(request: Request, db: Session = Depends(get_db)) -> list[dict]:
    require_local_developer(request)
    traders = list(db.scalars(select(Trader).order_by(Trader.id)).all())
    return [{"id": t.id, "name": t.name, "trader_type": t.trader_type.value} for t in traders]


@router.post("/test/verify-idempotency")
def dev_verify_idempotency(request: Request, db: Session = Depends(get_db)) -> dict:
    require_local_developer(request)
    issues: list[str] = []
    from app.models import NewsEvent

    news_rows = db.scalar(select(func.count(NewsEvent.id))) or 0
    executed = db.scalar(
        select(func.count(TimelineEvent.id)).where(
            TimelineEvent.status == TimelineEventStatus.EXECUTED
        )
    ) or 0
    pending = db.scalar(
        select(func.count(TimelineEvent.id)).where(
            TimelineEvent.status == TimelineEventStatus.PENDING
        )
    ) or 0
    trade_count = db.scalar(select(func.count(Trade.id))) or 0
    ipo_count = db.scalar(select(func.count(IPO.id))) or 0

    dup_news = db.execute(
        select(NewsEvent.title, func.count(NewsEvent.id))
        .group_by(NewsEvent.title)
        .having(func.count(NewsEvent.id) > 1)
    ).all()
    if dup_news:
        issues.append(f"duplicate news titles: {len(dup_news)}")

    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "counts": {
            "news": int(news_rows),
            "executed_checkpoints": int(executed),
            "pending_checkpoints": int(pending),
            "trades": int(trade_count),
            "ipos": int(ipo_count),
        },
    }
