"""Push portfolio snapshots to Supabase (cloud) or LAN collector."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import Trade
from app.models.enums import TraderType
from app.models.trader import Trader
from app.services.portfolio_service import get_portfolio, get_wallet

logger = logging.getLogger(__name__)

_sync_task: asyncio.Task | None = None


def build_snapshot_payload(db: Session, trader_id: int) -> dict:
    trader = db.get(Trader, trader_id)
    if trader is None:
        raise ValueError("trader not found")
    wallet = get_wallet(db, trader_id)
    portfolio = get_portfolio(db, trader_id)
    trade_count = db.scalar(
        select(func.count(Trade.id)).where(
            (Trade.buyer_id == trader_id) | (Trade.seller_id == trader_id)
        )
    ) or 0

    holdings = []
    for h in portfolio.holdings:
        holdings.append(
            {
                "ticker": h.ticker,
                "quantity": h.quantity,
                "avg_cost": str(h.avg_cost),
            }
        )

    session_id = trader.session_id or get_settings().participant_session_id or str(trader.id)
    return {
        "display_name": trader.name,
        "session_id": session_id,
        "cash": str(wallet.available_cash),
        "holdings": holdings,
        "realized_pnl": str(portfolio.realized_pnl),
        "unrealized_pnl": str(portfolio.unrealized_pnl),
        "portfolio_value": str(portfolio.portfolio_value),
        "return_pct": str(portfolio.return_pct),
        "trade_count": int(trade_count),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _supabase_row(payload: dict, table: str) -> dict:
    return {
        "session_id": payload["session_id"],
        "display_name": payload["display_name"],
        "cash": float(payload["cash"]),
        "holdings_json": payload["holdings"],
        "realized_pnl": float(payload["realized_pnl"]),
        "unrealized_pnl": float(payload["unrealized_pnl"]),
        "portfolio_value": float(payload["portfolio_value"]),
        "return_pct": float(payload["return_pct"]),
        "trade_count": payload["trade_count"],
        "updated_at": payload["timestamp"],
    }


async def push_snapshot_supabase(payload: dict) -> bool:
    settings = get_settings()
    base = (settings.supabase_url or "").strip().rstrip("/")
    key = (settings.supabase_anon_key or "").strip()
    if not base or not key:
        return False
    table = settings.supabase_leaderboard_table
    url = f"{base}/rest/v1/{table}?on_conflict=session_id"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(url, headers=headers, json=_supabase_row(payload, table))
            if res.status_code >= 400:
                logger.warning("Supabase sync failed: %s %s", res.status_code, res.text[:200])
                return False
        return True
    except Exception:  # noqa: BLE001
        logger.debug("Supabase sync error", exc_info=True)
        return False


async def push_snapshot_http(payload: dict, url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(url, json=payload)
            if res.status_code >= 400:
                logger.warning("Leaderboard sync failed: %s %s", res.status_code, res.text[:200])
                return False
        return True
    except Exception:  # noqa: BLE001
        logger.debug("Leaderboard sync error", exc_info=True)
        return False


async def push_snapshot(trader_id: int) -> bool:
    settings = get_settings()
    with SessionLocal() as db:
        payload = build_snapshot_payload(db, trader_id)

    if settings.supabase_url and settings.supabase_anon_key:
        return await push_snapshot_supabase(payload)

    url = (settings.leaderboard_sync_url or "").strip()
    if url:
        return await push_snapshot_http(payload, url)
    return False


def leaderboard_sync_configured() -> bool:
    settings = get_settings()
    if settings.participant_event_mode:
        return False
    if settings.supabase_url and settings.supabase_anon_key:
        return True
    return bool((settings.leaderboard_sync_url or "").strip())


async def _sync_loop() -> None:
    settings = get_settings()
    interval = max(15.0, float(settings.leaderboard_sync_interval_sec))
    while True:
        await asyncio.sleep(interval)
        try:
            with SessionLocal() as db:
                traders = list(
                    db.scalars(
                        select(Trader).where(Trader.trader_type == TraderType.HUMAN)
                    ).all()
                )
                for trader in traders:
                    await push_snapshot(trader.id)
        except Exception:  # noqa: BLE001
            logger.debug("Leaderboard sync loop error", exc_info=True)


def start_leaderboard_sync() -> None:
    global _sync_task
    settings = get_settings()
    if not leaderboard_sync_configured():
        return
    if _sync_task and not _sync_task.done():
        return
    _sync_task = asyncio.create_task(_sync_loop())
    if settings.supabase_url:
        logger.info("Leaderboard sync started → Supabase %s", settings.supabase_leaderboard_table)
    else:
        logger.info("Leaderboard sync started → %s", settings.leaderboard_sync_url)


def stop_leaderboard_sync() -> None:
    global _sync_task
    if _sync_task:
        _sync_task.cancel()
        _sync_task = None


def _supabase_headers() -> tuple[str, dict[str, str]] | None:
    settings = get_settings()
    base = (settings.supabase_url or "").strip().rstrip("/")
    key = (settings.supabase_anon_key or "").strip()
    if not base or not key:
        return None
    return base, {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


async def signal_global_reset() -> bool:
    """Bump event_control.reset_at so all participant clients reset local sims."""
    cfg = _supabase_headers()
    if cfg is None:
        return False
    base, headers = cfg
    settings = get_settings()
    table = settings.supabase_event_control_table
    url = f"{base}/rest/v1/{table}?on_conflict=id"
    headers = {**headers, "Prefer": "resolution=merge-duplicates,return=minimal"}
    payload = {
        "id": 1,
        "reset_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(url, headers=headers, json=payload)
            if res.status_code >= 400:
                logger.warning("event_control signal failed: %s %s", res.status_code, res.text[:200])
                return False
        return True
    except Exception:  # noqa: BLE001
        logger.debug("event_control signal error", exc_info=True)
        return False


async def clear_supabase_leaderboard() -> bool:
    """Remove all participant snapshot rows after a full market reset."""
    cfg = _supabase_headers()
    if cfg is None:
        return False
    base, headers = cfg
    settings = get_settings()
    table = settings.supabase_leaderboard_table
    url = f"{base}/rest/v1/{table}?return_pct=gte.-1000"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.delete(url, headers=headers)
            if res.status_code >= 400:
                logger.warning("leaderboard clear failed: %s %s", res.status_code, res.text[:200])
                return False
        return True
    except Exception:  # noqa: BLE001
        logger.debug("leaderboard clear error", exc_info=True)
        return False


async def clear_supabase_snapshot(session_id: str) -> bool:
    """Remove one participant row from the cloud leaderboard."""
    cfg = _supabase_headers()
    if cfg is None or not session_id:
        return False
    base, headers = cfg
    settings = get_settings()
    table = settings.supabase_leaderboard_table
    url = f"{base}/rest/v1/{table}?session_id=eq.{session_id}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.delete(url, headers=headers)
            if res.status_code >= 400:
                logger.warning(
                    "snapshot clear failed: %s %s", res.status_code, res.text[:200]
                )
                return False
        return True
    except Exception:  # noqa: BLE001
        logger.debug("snapshot clear error", exc_info=True)
        return False
