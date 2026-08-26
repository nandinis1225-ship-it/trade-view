"""Offline edition verification — determinism + collector sync."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models import Stock
from app.services.ipo_service import allot_ipo_personal, apply_ipo, create_ipo, open_ipo
from app.services.leaderboard_sync_service import build_snapshot_payload
from app.services.market_pulse_service import run_market_pulse
from app.services.simulation_controller import bootstrap_universe
from app.services.trader_service import create_trader
from app.schemas import TraderCreate
from app.models.enums import TraderType


def test_universe_has_35_tradable_stocks(db_session):
    bootstrap_universe(db_session)
    count = db_session.scalar(select(func.count(Stock.id))) or 0
    assert count == 35


def test_pulse_determinism_repeated(db_session):
    bootstrap_universe(db_session)
    stocks = list(db_session.scalars(select(Stock).order_by(Stock.ticker)).all())

    def capture_after_two_pulses() -> dict[str, str]:
        for stock in stocks:
            stock.last_traded_price = stock.starting_price
            stock.fair_value = stock.starting_price
        db_session.commit()
        run_market_pulse(db_session, 120.0, pulse_seq=1)
        run_market_pulse(db_session, 120.0, pulse_seq=2)
        db_session.expire_all()
        refreshed = list(db_session.scalars(select(Stock).order_by(Stock.ticker)).all())
        return {s.ticker: str(s.last_traded_price) for s in refreshed}

    prices_a = capture_after_two_pulses()
    prices_b = capture_after_two_pulses()
    assert prices_a == prices_b


def test_personal_ipo_allotment(db_session):
    trader = create_trader(
        db_session,
        TraderCreate(name="Alice", trader_type=TraderType.HUMAN, session_id="sess-a"),
    )
    ipo = create_ipo(
        db_session,
        company_name="Future Capital",
        ticker="FCH",
        issue_price=765,
        lot_size=18,
        total_lots=800,
        winning_lots=200,
        maximum_lots_per_user=2,
    )
    open_ipo(db_session, ipo.id)
    apply_ipo(db_session, ipo_id=ipo.id, trader_id=trader.id, requested_lots=2)
    result = allot_ipo_personal(db_session, ipo.id)
    assert "allocations" in result
    assert result["allotment_mode"] == "personal"


def test_snapshot_payload(db_session):
    trader = create_trader(
        db_session,
        TraderCreate(name="Bob", trader_type=TraderType.HUMAN, session_id="sess-b"),
    )
    payload = build_snapshot_payload(db_session, trader.id)
    assert payload["display_name"] == "Bob"
    assert payload["session_id"] == "sess-b"
    assert "portfolio_value" in payload
