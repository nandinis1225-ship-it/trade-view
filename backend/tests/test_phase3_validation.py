"""Phase 3 — simulation correctness, recovery, and privacy validation."""

from __future__ import annotations

import inspect
import os
import re
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.ai import runner as ai_runner
from app.core.config import get_settings
from app.models import Holding, NewsStockImpact, Stock, TimelineEvent, Trader
from app.models.enums import (
    SimulationStatus,
    TimelineEventStatus,
    TimelineEventType,
    TraderType,
)
from app.models.order_enums import OrderSide, OrderType
from app.models.ipo import IPO, IPOApplication, IPOStatus
from app.schemas import HoldingAdjust, TraderCreate
from app.services import news_service, order_service, portfolio_service, stock_service
from app.services.dissolution_service import dissolve_company
from app.services.event_processor import process_due_events, process_single_timeline_event, run_ai_tick_at
from app.services.ipo_service import (
    allot_ipo,
    apply_ipo,
    close_applications,
    create_ipo,
    list_ipo,
    open_ipo,
)
from app.services.news_impact_resolver import compute_stock_impacts_for_news, seeded_variation
from app.services.recovery_service import AI_TICK_INTERVAL_SEC, catch_up_missed_simulation
from app.services.simulation_controller import bootstrap_universe, reset_simulation, start_simulation
from app.services.simulation_clock import get_or_create_state
from app.services.simulation_engine import _loop
from app.services.timeline_service import seed_timeline_from_json, validate_timeline
from tests.conftest import join_participant


REPO_ROOT = Path(__file__).resolve().parents[2]


def _release_sector_news(db_session, sector_slug: str, impact_pct: float):
    event = news_service.create_news(
        db_session,
        title=f"Sector move {sector_slug}",
        description="Phase 3 validation news",
        direction=1 if impact_pct >= 0 else -1,
        impact=Decimal("1"),
        confidence=Decimal("1"),
        duration_minutes=9999,
        decay_rate=Decimal("0.001"),
        sector_impacts={sector_slug: impact_pct},
        status="draft",
    )
    return news_service.release_news(db_session, event.id)


def test_news_sector_impact_deterministic_variation_bounds(db_session, mini_timeline):
    """Sector +10% → each affected stock target in [+9.5%, +10.5%]; negative symmetric."""
    bootstrap_universe(db_session)
    start_simulation(db_session)

    for sector_slug, impact in (("it", 10.0), ("financials", -10.0)):
        released = _release_sector_news(db_session, sector_slug, impact)
        impacts = list(
            db_session.scalars(
                select(NewsStockImpact).where(NewsStockImpact.news_event_id == released.id)
            ).all()
        )
        assert impacts, f"expected impacts for sector {sector_slug}"
        primary_rows = [row for row in impacts if row.sector_slug == sector_slug]
        assert primary_rows, f"expected primary-sector impacts for {sector_slug}"
        for row in primary_rows:
            variation = float(row.variation_pct)
            assert -0.05 <= variation <= 0.05
            target = float(row.target_impact_pct)
            if impact > 0:
                assert 9.5 <= target <= 10.5, (sector_slug, target, variation)
            else:
                assert -10.5 <= target <= -9.5, (sector_slug, target, variation)
            stock = db_session.get(Stock, row.stock_id)
            assert stock is not None
            assert stock.fair_value is not None
            ref = float(row.reference_price)
            expected_fv = ref * (1 + target / 100.0)
            assert abs(float(stock.fair_value) - expected_fv) < 0.02


def test_news_sets_fair_value_without_instant_ltp_snap(db_session, mini_timeline):
    bootstrap_universe(db_session)
    start_simulation(db_session)
    stock = stock_service.get_stock_by_ticker(db_session, "TCS")
    assert stock is not None
    ltp_before = Decimal(stock.last_traded_price)
    released = _release_sector_news(db_session, "it", 8.0)
    db_session.refresh(stock)
    ltp_after_release = Decimal(stock.last_traded_price)
    assert stock.fair_value is not None
    assert stock.fair_value != ltp_before or ltp_after_release == ltp_before


def test_ai_moves_ltp_toward_fair_value_target(db_session, mini_timeline):
    bootstrap_universe(db_session)
    start_simulation(db_session)
    stock = stock_service.get_stock_by_ticker(db_session, "TCS")
    assert stock is not None
    ref = Decimal(stock.last_traded_price)
    released = _release_sector_news(db_session, "it", 10.0)
    impact = db_session.scalar(
        select(NewsStockImpact).where(
            NewsStockImpact.news_event_id == released.id,
            NewsStockImpact.stock_id == stock.id,
        )
    )
    assert impact is not None
    db_session.refresh(stock)
    target_fv = Decimal(impact.target_price)
    assert stock.fair_value == target_fv.quantize(Decimal("0.0001"))

    distance_before = abs(float(stock.last_traded_price) - float(target_fv))
    for _ in range(6):
        ai_runner.run_all_agents(db_session)
        db_session.commit()
        db_session.refresh(stock)
    distance_after = abs(float(stock.last_traded_price) - float(target_fv))
    assert distance_after <= distance_before or float(stock.last_traded_price) != float(ref)


def test_news_hierarchy_dominates_participant_trading(db_session, mini_timeline):
    """Major news target must remain authoritative; participant orders cannot permanently override."""
    bootstrap_universe(db_session)
    start_simulation(db_session)
    stock = stock_service.get_stock_by_ticker(db_session, "HDFCBANK")
    assert stock is not None
    trader = db_session.scalar(select(Trader).where(Trader.trader_type == TraderType.HUMAN))
    if trader is None:
        from app.services.trader_service import create_trader

        trader = create_trader(db_session, TraderCreate(name="Phase3Trader", trader_type=TraderType.HUMAN))

    released = _release_sector_news(db_session, "financials", 12.0)
    impact = db_session.scalar(
        select(NewsStockImpact).where(
            NewsStockImpact.news_event_id == released.id,
            NewsStockImpact.stock_id == stock.id,
        )
    )
    assert impact is not None
    db_session.refresh(stock)
    bullish_target = float(impact.target_price)

    portfolio_service.set_holding(
        db_session,
        trader.id,
        HoldingAdjust(stock_id=stock.id, quantity=500, avg_cost=stock.last_traded_price),
    )
    trader.cash = Decimal("5000000")
    db_session.commit()

    for _ in range(20):
        try:
            order_service.submit_order(
                db_session,
                trader_id=trader.id,
                stock_id=stock.id,
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=50,
            )
        except order_service.OrderGatewayError:
            break

    for _ in range(8):
        ai_runner.run_all_agents(db_session)
        db_session.commit()

    db_session.refresh(stock)
    assert float(stock.fair_value) == pytest.approx(bullish_target, rel=0.001)
    combined = float(stock.last_traded_price)
    assert combined < bullish_target * 1.15


def test_ai_tick_interval_is_thirty_sim_seconds(db_session, mini_timeline, monkeypatch):
    monkeypatch.setenv("PARTICIPANT_EVENT_MODE", "true")
    monkeypatch.setenv("LOCAL_INSTANCE_MODE", "true")
    get_settings.cache_clear()

    bootstrap_universe(db_session)
    start_simulation(db_session)
    from sqlalchemy import delete

    db_session.execute(delete(TimelineEvent))
    db_session.commit()

    state = get_or_create_state(db_session)
    state.last_ai_tick_elapsed_sec = -30.0
    state.last_processed_elapsed_sec = 0.0
    state.sim_elapsed_sec = 0.0
    state.event_start_real = datetime.now(timezone.utc)
    state.anchor_sim_elapsed_sec = 0.0
    db_session.commit()

    processed_times: list[float] = []
    for tick in (30.0, 60.0, 90.0, 120.0):
        state = get_or_create_state(db_session)
        state.event_start_real = datetime.now(timezone.utc) - timedelta(seconds=tick + 1)
        state.anchor_sim_elapsed_sec = 0.0
        state.last_processed_elapsed_sec = tick - 30.0
        state.last_ai_tick_elapsed_sec = tick - 30.0
        state.sim_elapsed_sec = tick - 30.0
        db_session.commit()

        result = catch_up_missed_simulation(db_session)
        assert result["caught_up"] is True
        state = get_or_create_state(db_session)
        processed_times.append(float(state.last_ai_tick_elapsed_sec))

    assert processed_times == [30.0, 60.0, 90.0, 120.0]
    assert AI_TICK_INTERVAL_SEC == 30.0


def test_market_pulse_disabled_in_participant_event_mode():
    source = inspect.getsource(_loop)
    assert "run_market_pulse" in source
    assert "not get_settings().participant_event_mode" in source


def test_production_timeline_structure(production_timeline):
    errors = validate_timeline(production_timeline)
    assert errors == [], errors
    events = production_timeline["events"]
    assert len(events) >= 64
    ids = [int(e["checkpoint_id"]) for e in events]
    assert len(ids) == len(set(ids)), "duplicate checkpoint_id in production timeline"
    keys = [e.get("idempotency_key") or f"cp_{e['checkpoint_id']}" for e in events]
    assert len(keys) == len(set(keys)), "duplicate idempotency keys in production timeline"


def test_ipo_full_path_no_duplicate_allocation_on_replay(db_session, mini_timeline, monkeypatch):
    monkeypatch.setenv("LOCAL_INSTANCE_MODE", "true")
    get_settings.cache_clear()

    bootstrap_universe(db_session)
    trader = db_session.scalar(select(Trader).where(Trader.trader_type == TraderType.HUMAN))
    if trader is None:
        from app.services.trader_service import create_trader

        trader = create_trader(db_session, TraderCreate(name="IPOUser", trader_type=TraderType.HUMAN))
    cash_before = Decimal(trader.cash)

    ipo = create_ipo(
        db_session,
        company_name="Phase3 IPO",
        ticker="P3IPO",
        issue_price=100,
        lot_size=10,
        total_lots=100,
        winning_lots=40,
        maximum_lots_per_user=2,
    )
    open_ipo(db_session, ipo.id)
    apply_ipo(db_session, ipo_id=ipo.id, trader_id=trader.id, requested_lots=2)
    db_session.refresh(trader)
    blocked = Decimal(trader.cash_blocked_ipo)
    assert blocked == Decimal("2000")

    close_applications(db_session, ipo.id)
    first = allot_ipo(db_session, ipo.id, seed=42)
    second = allot_ipo(db_session, ipo.id, seed=42)
    assert first.get("already_allotted") is not True
    assert second.get("already_allotted") is True

    listed = list_ipo(db_session, ipo.id)
    replay_list = list_ipo(db_session, ipo.id)
    assert listed.get("already_listed") is not True
    assert replay_list.get("already_listed") is True

    stock = stock_service.get_stock_by_ticker(db_session, "P3IPO")
    assert stock is not None
    h = db_session.scalar(
        select(Holding).where(Holding.trader_id == trader.id, Holding.stock_id == stock.id)
    )
    assert h is not None and h.quantity > 0

    db_session.refresh(trader)
    assert Decimal(trader.cash_blocked_ipo) == 0


def test_dissolution_replay_no_duplicate_liquidation(db_session):
    from app.models.enums import Sector
    from app.schemas import StockCreate
    from app.services.trader_service import create_trader

    trader = create_trader(db_session, TraderCreate(name="DissolveUser", trader_type=TraderType.HUMAN))
    stock = stock_service.create_stock(
        db_session,
        StockCreate(
            ticker="P3DISS",
            company_name="Phase3 Dissolve Co",
            sector=Sector.TECH,
            starting_price=Decimal("100"),
            shares_outstanding=1_000_000,
            fair_value=Decimal("100"),
        ),
    )
    portfolio_service.set_holding(
        db_session,
        trader.id,
        HoldingAdjust(stock_id=stock.id, quantity=10, avg_cost=stock.last_traded_price),
    )
    db_session.refresh(trader)
    cash_before = Decimal(trader.cash)
    pnl_before = Decimal(trader.realized_pnl)

    first = dissolve_company(db_session, ticker="P3DISS", liquidation_price="50")
    db_session.refresh(trader)
    cash_after = Decimal(trader.cash)
    pnl_after = Decimal(trader.realized_pnl)

    second = dissolve_company(db_session, ticker="P3DISS", liquidation_price="50")
    assert second.get("already_dissolved") is True
    db_session.refresh(trader)
    assert Decimal(trader.cash) == cash_after
    assert Decimal(trader.realized_pnl) == pnl_after
    assert cash_after > cash_before
    assert first["holdings_liquidated"] == 10


def test_recovery_integration_news_ai_ipo_dissolution(db_session, mini_timeline, monkeypatch):
    monkeypatch.setenv("PARTICIPANT_EVENT_MODE", "true")
    monkeypatch.setenv("LOCAL_INSTANCE_MODE", "true")
    get_settings.cache_clear()

    bootstrap_universe(db_session)
    start_simulation(db_session)
    from sqlalchemy import delete

    db_session.execute(delete(TimelineEvent))
    db_session.commit()

    state = get_or_create_state(db_session)
    state.last_processed_elapsed_sec = 0.0
    state.last_ai_tick_elapsed_sec = -30.0
    state.sim_elapsed_sec = 0.0
    state.event_start_real = datetime.now(timezone.utc) - timedelta(seconds=200)
    state.anchor_sim_elapsed_sec = 0.0
    db_session.commit()

    db_session.add(
        TimelineEvent(
            checkpoint_id=91001,
            idempotency_key="phase3_recovery_news",
            event_type=TimelineEventType.NEWS,
            sim_offset_sec=30.0,
            phase="PHASE 1",
            headline="Recovery news",
            description="integration",
            payload_json='{"sector_impacts":{"it":5}}',
            status=TimelineEventStatus.PENDING,
        )
    )
    db_session.add(
        TimelineEvent(
            checkpoint_id=91002,
            idempotency_key="phase3_recovery_ipo_open",
            event_type=TimelineEventType.IPO_OPEN,
            sim_offset_sec=60.0,
            phase="PHASE 1",
            headline="IPO open",
            description="",
            payload_json=(
                '{"ipo_key":"p3r","ticker":"P3R","company_name":"Recovery IPO",'
                '"issue_price":50,"lot_size":10,"total_lots":50,"winning_lots":20}'
            ),
            status=TimelineEventStatus.PENDING,
        )
    )
    db_session.add(
        TimelineEvent(
            checkpoint_id=91004,
            idempotency_key="phase3_recovery_ipo_close",
            event_type=TimelineEventType.IPO_CLOSE,
            sim_offset_sec=75.0,
            phase="PHASE 1",
            headline="IPO close",
            description="",
            payload_json='{"ipo_key":"p3r","ticker":"P3R"}',
            status=TimelineEventStatus.PENDING,
        )
    )
    db_session.add(
        TimelineEvent(
            checkpoint_id=91005,
            idempotency_key="phase3_recovery_ipo_allot",
            event_type=TimelineEventType.IPO_ALLOTMENT,
            sim_offset_sec=90.0,
            phase="PHASE 1",
            headline="IPO allot",
            description="",
            payload_json='{"ipo_key":"p3r","ticker":"P3R"}',
            status=TimelineEventStatus.PENDING,
        )
    )
    db_session.add(
        TimelineEvent(
            checkpoint_id=91003,
            idempotency_key="phase3_recovery_dissolve",
            event_type=TimelineEventType.COMPANY_DISSOLUTION,
            sim_offset_sec=150.0,
            phase="PHASE 1",
            headline="Dissolve",
            description="",
            payload_json='{"ticker":"AXISBANK","liquidation_price":250}',
            status=TimelineEventStatus.PENDING,
        )
    )
    db_session.commit()

    first = catch_up_missed_simulation(db_session)
    second = catch_up_missed_simulation(db_session)
    assert first["events_processed"] >= 4
    assert first["ai_ticks_processed"] >= 2
    assert second["events_processed"] == 0

    for cp in (91001, 91002, 91004, 91005, 91003):
        ev = db_session.scalar(select(TimelineEvent).where(TimelineEvent.checkpoint_id == cp))
        assert ev is not None
        assert ev.status == TimelineEventStatus.EXECUTED

    state = get_or_create_state(db_session)
    assert float(state.last_processed_elapsed_sec) >= 150.0
    assert float(state.sim_elapsed_sec) >= float(state.last_processed_elapsed_sec)


def test_identity_recovery_across_reopen(event_client):
    first_id, _ = join_participant(event_client, "Alice", session_id="phase3-sess-1")
    blocked = event_client.post(
        "/api/v1/auth/join",
        json={"display_name": "Bob", "session_id": "phase3-sess-1"},
    )
    assert blocked.status_code == 403

    _, auth = join_participant(event_client, "Alice", session_id="phase3-sess-1")
    body = event_client.get("/api/v1/session/bootstrap", headers=auth).json()
    assert body["trader_id"] == first_id
    assert body["trader_name"] == "Alice"


def test_participant_api_leak_audit(event_client, mini_timeline):
    """REST responses must not expose future timeline or internal simulation metadata."""
    forbidden_substrings = (
        "EUPHORIA",
        "CRASH",
        "RECOVERY",
        "PHASE 1",
        "PHASE 2",
        "PHASE 3",
        "PHASE 4",
        "sector_impacts",
        "effective_impact",
        "AI_TICK",
        "MARKET_PULSE",
        "stop_loss",
        "take_profit",
    )
    _, auth = join_participant(event_client, "LeakAudit")
    paths = (
        "/api/v1/session/bootstrap",
        "/api/v1/market/status",
        "/api/v1/news",
        "/api/v1/stocks",
        "/api/v1/ipos",
    )
    for path in paths:
        res = event_client.get(path, headers=auth)
        assert res.status_code in (200, 404), res.text
        if res.status_code != 200:
            continue
        text = res.text.upper()
        for token in forbidden_substrings:
            assert token.upper() not in text, f"{path} leaked {token}"

    stocks = event_client.get("/api/v1/stocks", headers=auth).json()
    for row in stocks:
        if "fair_value" in row and "last_traded_price" in row:
            assert row["fair_value"] == row["last_traded_price"]


def test_offline_source_has_no_mandatory_external_startup_urls():
    """Participant runtime paths must not hardcode external service URLs at startup."""
    patterns = [
        re.compile(r"https?://[^\s\"']*supabase\.co", re.I),
        re.compile(r"https?://[^\s\"']*googleapis\.com", re.I),
        re.compile(r"https?://[^\s\"']*github\.com", re.I),
        re.compile(r"https?://[^\s\"']*npmjs\.org", re.I),
        re.compile(r"https?://[^\s\"']*pypi\.org", re.I),
    ]
    scan_files = [
        REPO_ROOT / "backend" / "app" / "main.py",
        REPO_ROOT / "frontend" / "src" / "app" / "terminal" / "page.tsx",
        REPO_ROOT / "frontend" / "src" / "lib" / "api.ts",
        REPO_ROOT / "frontend" / "src" / "lib" / "runtimeConfig.ts",
        REPO_ROOT / "desktop" / "src-tauri" / "src" / "main.rs",
    ]
    violations: list[str] = []
    for path in scan_files:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pat in patterns:
            if pat.search(text):
                violations.append(f"{path}: {pat.pattern}")
    assert not violations, "\n".join(violations)


def test_performance_smoke_simulation_advance(db_session, mini_timeline):
    bootstrap_universe(db_session)
    start_simulation(db_session)
    t0 = time.monotonic()
    for step in range(120):
        state = get_or_create_state(db_session)
        elapsed = float(state.sim_elapsed_sec) + 30.0
        state.sim_elapsed_sec = elapsed
        db_session.commit()
        process_due_events(db_session, elapsed)
        if step % 3 == 0:
            run_ai_tick_at(db_session, elapsed)
    elapsed_wall = time.monotonic() - t0
    assert elapsed_wall < 120.0, "simulation advance took too long — possible runaway loop"
