"""Cross-sector news propagation — relationship graph and safety rules."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services import news_service
from app.services.news_impact_resolver import sector_impact_for_stock
from app.services.sector_relationships import expand_sector_impacts
from app.services.simulation_controller import bootstrap_universe, start_simulation
from app.services.stock_service import get_stock_by_ticker
from app.models import NewsStockImpact
from sqlalchemy import select


def test_infrastructure_primary_propagates_to_related_sectors(db_session, mini_timeline):
    bootstrap_universe(db_session)
    primary = 5.0
    expanded = expand_sector_impacts({"infrastructure": primary})
    assert expanded["infrastructure"] == primary
    assert expanded["industrials"] == pytest.approx(3.0)
    assert expanded["energy"] == pytest.approx(2.5)
    assert expanded["metals"] == pytest.approx(2.0)
    assert expanded["financials"] == pytest.approx(1.5)
    assert "consumer" not in expanded


def test_negative_primary_sign_propagates(db_session, mini_timeline):
    expanded = expand_sector_impacts({"infrastructure": -5.0})
    assert expanded["metals"] == pytest.approx(-2.0)


def test_energy_positive_hurts_automobiles(db_session, mini_timeline):
    expanded = expand_sector_impacts({"energy": 5.0})
    assert expanded["automobiles"] == pytest.approx(-1.25)


def test_energy_negative_helps_automobiles(db_session, mini_timeline):
    expanded = expand_sector_impacts({"energy": -5.0})
    assert expanded["automobiles"] == pytest.approx(1.25)


def test_secondary_never_exceeds_primary_magnitude(db_session, mini_timeline):
    expanded = expand_sector_impacts({"financials": 2.0})
    for slug, pct in expanded.items():
        if slug != "financials":
            assert abs(pct) <= 2.0


def test_primary_sector_strongest_for_its_own_stocks(db_session, mini_timeline):
    bootstrap_universe(db_session)
    start_simulation(db_session)
    event = news_service.create_news(
        db_session,
        title="Infra boom",
        description="test",
        direction=1,
        impact=Decimal("1"),
        confidence=Decimal("1"),
        duration_minutes=9999,
        decay_rate=Decimal("0.001"),
        sector_impacts={"infrastructure": 5.0},
        status="draft",
    )
    news_service.release_news(db_session, event.id)
    infra_stock = get_stock_by_ticker(db_session, "GMRINFRA")
    industrial_stock = get_stock_by_ticker(db_session, "LT")
    assert infra_stock and industrial_stock
    infra_pct = sector_impact_for_stock(event, infra_stock)
    industrial_pct = sector_impact_for_stock(event, industrial_stock)
    assert infra_pct == 5.0
    assert industrial_pct == pytest.approx(3.0)
    assert abs(infra_pct) > abs(industrial_pct)


def test_market_wide_applies_sector_multipliers(db_session, mini_timeline):
    expanded = expand_sector_impacts({}, market_wide_base=3.0)
    assert expanded["financials"] == pytest.approx(3.0)
    assert expanded["it"] == pytest.approx(2.7)
    assert expanded["consumer"] == pytest.approx(2.1)
    assert len(expanded) == 9


def test_cross_sector_stock_impacts_and_fair_value(db_session, mini_timeline):
    bootstrap_universe(db_session)
    start_simulation(db_session)
    event = news_service.create_news(
        db_session,
        title="Infra spending",
        description="test",
        direction=1,
        impact=Decimal("1"),
        confidence=Decimal("1"),
        duration_minutes=9999,
        decay_rate=Decimal("0.001"),
        sector_impacts={"infrastructure": 5.0},
        status="draft",
    )
    news_service.release_news(db_session, event.id)
    industrial = get_stock_by_ticker(db_session, "BHEL")
    assert industrial is not None
    row = db_session.scalar(
        select(NewsStockImpact).where(
            NewsStockImpact.news_event_id == event.id,
            NewsStockImpact.stock_id == industrial.id,
        )
    )
    assert row is not None
    assert row.sector_slug == "industrials"
    assert float(row.sector_impact_pct) == pytest.approx(3.0)
    variation = float(row.variation_pct)
    assert -0.05 <= variation <= 0.05
    assert 2.85 <= float(row.target_impact_pct) <= 3.15
    db_session.refresh(industrial)
    assert industrial.fair_value is not None
    ltp = float(industrial.last_traded_price)
    assert ltp == pytest.approx(float(industrial.starting_price), rel=0.001)


def test_unrelated_sector_zero_impact(db_session, mini_timeline):
    bootstrap_universe(db_session)
    event = news_service.create_news(
        db_session,
        title="IT exports",
        description="test",
        direction=1,
        impact=Decimal("1"),
        confidence=Decimal("1"),
        duration_minutes=9999,
        decay_rate=Decimal("0.001"),
        sector_impacts={"it": 4.0},
        status="draft",
    )
    news_service.release_news(db_session, event.id)
    metal = get_stock_by_ticker(db_session, "SAIL")
    assert metal is not None
    assert sector_impact_for_stock(event, metal) is None
