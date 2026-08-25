"""Load TRADEVERSE universe from tradeverse_universe.json (ground truth for local edition)."""

from __future__ import annotations

import json
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.enums import (
    FundamentalProfile,
    LiquidityClass,
    Sector,
    VolatilityClass,
)
from app.schemas import StockCreate
from app.services import sector_service, stock_service

UNIVERSE_PATH = Path(__file__).resolve().parent / "tradeverse_universe.json"

VOLATILITY_MAP: dict[str, VolatilityClass] = {
    "low": VolatilityClass.LOW,
    "medium": VolatilityClass.MEDIUM,
    "high": VolatilityClass.HIGH,
    "very_high": VolatilityClass.VERY_HIGH,
}

SLUG_TO_ENUM: dict[str, Sector] = {
    "financials": Sector.FINANCE,
    "it": Sector.TECH,
    "automobiles": Sector.AUTO,
    "energy": Sector.ENERGY,
    "industrials": Sector.INDUSTRIALS,
    "infrastructure": Sector.INFRA,
    "real_estate": Sector.REAL_ESTATE,
    "metals": Sector.INDUSTRIALS,
    "consumer": Sector.RETAIL,
}


@lru_cache(maxsize=1)
def load_universe() -> dict[str, Any]:
    with UNIVERSE_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def universe_constants() -> dict[str, Any]:
    data = load_universe()
    return {
        "sim_duration_sec": float(data.get("sim_duration_sec", 10800)),
        "default_starting_capital": float(data.get("default_starting_capital", 500000)),
        "max_position_per_stock": int(data.get("max_position_per_stock", 100)),
        "default_tick_size": float(data.get("default_tick_size", 0.05)),
        "default_circuit_pct": float(data.get("default_circuit_pct", 0.10)),
        "default_simulation_seed": int(data.get("default_simulation_seed", 42)),
    }


def canonical_tradable_count() -> int:
    return len(load_universe().get("tradable_stocks", []))


def canonical_ipo_count() -> int:
    return len(load_universe().get("ipo_definitions", []))


def canonical_total_count() -> int:
    return canonical_tradable_count() + canonical_ipo_count()


def canonical_tradable_tickers() -> frozenset[str]:
    return frozenset(
        row["ticker"].upper() for row in load_universe().get("tradable_stocks", [])
    )


def ipo_definition_by_ticker(ticker: str) -> dict | None:
    key = ticker.strip().upper()
    for row in load_universe().get("ipo_definitions", []):
        if row.get("ticker", "").upper() == key:
            return row
    return None


def ipo_definition_by_key(ipo_key: str) -> dict | None:
    key = ipo_key.strip().lower()
    for row in load_universe().get("ipo_definitions", []):
        if row.get("ipo_key", "").lower() == key:
            return row
    return None


def resolve_ipo_sector_id(db: Session, ticker: str) -> int | None:
    defn = ipo_definition_by_ticker(ticker)
    if defn is None:
        return None
    slug = defn.get("sector_slug")
    if not slug:
        return None
    sector = sector_service.get_sector_by_slug(db, slug)
    return sector.id if sector else None


def seed_sectors_from_json(db: Session) -> int:
    created = 0
    for row in load_universe().get("sectors", []):
        slug = row["slug"]
        existing = sector_service.get_sector_by_slug(db, slug)
        if existing:
            continue
        from app.models.sector import MarketSector

        db.add(
            MarketSector(
                slug=slug,
                name=row["name"],
                display_order=int(row.get("display_order", 0)),
                is_active=True,
            )
        )
        created += 1
    if created:
        db.commit()
    return created


def seed_stocks_from_json(db: Session, *, skip_existing: bool = True) -> int:
    sector_service.ensure_sectors(db)
    created = 0
    tick_size = Decimal(str(universe_constants()["default_tick_size"]))

    for row in load_universe().get("tradable_stocks", []):
        ticker = row["ticker"].upper()
        if skip_existing and stock_service.get_stock_by_ticker(db, ticker):
            continue
        if stock_service.get_stock_by_ticker(db, ticker):
            continue

        slug = row.get("sector_slug", "")
        sector_enum = SLUG_TO_ENUM.get(slug, Sector.TECH)
        sector_row = sector_service.get_sector_by_slug(db, slug)
        vol_key = str(row.get("volatility_class", "medium")).lower()
        vol = VOLATILITY_MAP.get(vol_key, VolatilityClass.MEDIUM)
        price = Decimal(str(row["starting_price"]))

        stock_service.create_stock(
            db,
            StockCreate(
                ticker=ticker,
                company_name=row["company_name"],
                sector=sector_enum,
                sector_id=sector_row.id if sector_row else None,
                starting_price=price,
                shares_outstanding=50_000_000,
                fair_value=price,
                tick_size=tick_size,
                volatility_class=vol,
                liquidity_class=LiquidityClass.MEDIUM,
                fundamental_profile=FundamentalProfile.CYCLICAL,
                description=f"TRADEVERSE — {row['company_name']}",
            ),
        )
        created += 1

    sector_service.backfill_stock_sectors(db)
    return created


def apply_universe_simulation_settings(db: Session) -> None:
    from app.core.config import get_settings
    from app.services.simulation_settings_service import get_or_create_settings

    const = universe_constants()
    settings = get_or_create_settings(db)
    settings.sim_duration_sec = const["sim_duration_sec"]
    settings.simulation_seed = const["default_simulation_seed"]
    cfg = get_settings()
    settings.simulation_ai_enabled = bool(cfg.participant_event_mode or cfg.developer_mode)
    db.commit()

